#!/usr/bin/env python
# coding: utf-8



import numpy as np
import re
import pandas as pd
from sklearn.base import BaseEstimator,TransformerMixin


#import dataframe from scraped info
df = pd.read_csv("AllProperties.csv")
# no need to use the old index as there will  be duplicated values because of the append
df.drop("Unnamed: 0",axis=1,inplace=True)

#features list read in as string, convert to dictionary (alternatively pickle dataframe instead of saving as csv)
def compute_featuresdict(x):
    p = ["".join(i.split("'")[1:-1]) for i in x.replace("[","").replace("]","").split(", ") if "xa0" not in i]
    features_dict = {}
    for i in p:
        features,value = i.split(":")
        features_dict[features] = value
    return features_dict

#change the house prices to the naira,0 used as safeguard for any non-dollar 
def currency_changer(x):
    if "$" in x:
        return 480
    elif "₦" in x:
        return 1
    else:
        return 0
    
#convert address to categoricalvariable
def is_island(x):
    if ("ikoyi" in x.lower())|("victoria-island" in x.lower())|("ajah" in x.lower())|("lekki" in x.lower())|("eko-atlantic" in x.lower()):
        return 1
    else:
        return 0

#creating a class to transform the house data into meaningful array
class HouseFeatureTransformer(BaseEstimator,TransformerMixin):
    def __init__(self,add_extra_features = True):
        self.add_extra_features = add_extra_features
    def fit(self,x,y=None):
        return self
    def transform(self,x,y=None):
        features_kept = ["Listing Title","Listing Address","Latitude/Longitude","Descriptors","Flat","Distance to 3ML","Link"]
        features_dicts = x["Other Features"].apply(compute_featuresdict)
        Property_Ref = features_dicts.apply(lambda x:x.get("Property Ref").strip())
        Price = x["Listing Price"].apply(currency_changer)*x["Listing Price"].apply(lambda x:int(x.strip().split("per annum")[0].replace(",","").replace("₦","").replace("$","")))
        Date_Added = features_dicts.apply(lambda x:pd.to_datetime(x.get("Added On").strip()).date())
        Days_Since_Added = features_dicts.apply(lambda x:(pd.to_datetime("today").date() - pd.to_datetime(x.get("Added On").strip()).date()).days)
        Last_Updated = features_dicts.apply(lambda x:pd.to_datetime(x.get("Last Updated").strip()).date())
        Days_SinceUpdated = features_dicts.apply(lambda x:(pd.to_datetime("today").date() - pd.to_datetime(x.get("Last Updated").strip()).date()).days)
        Type = features_dicts.apply(lambda x:x.get("Type").strip())
        Bedrooms = features_dicts.apply(lambda x:int(x.get("Bedrooms")) if "Bedrooms" in x.keys() else 0)
        Bathrooms = features_dicts.apply(lambda x:int(x.get("Bathrooms")) if "Bathrooms" in x.keys() else 0)
        Toilets = features_dicts.apply(lambda x:int(x.get("Toilets")) if "Toilets" in x.keys() else 0)
        Parking_Spaces = features_dicts.apply(lambda x:int(x.get("Parking Spaces")) if "Parking Spaces" in x.keys() else np.nan)
        Serviced = features_dicts.apply(lambda x: x.get("Servicing") if "Servicing" in x.keys() else "0").apply(lambda x:0 if x=="0" else 1)
        Furnishing = features_dicts.apply(lambda x: x.get("Furnishing") if "Furnishing" in x.keys() else "0").apply(lambda x:0 if x=="0" else 1)
        Total_Area = features_dicts.apply(lambda x: x.get("Total Area").split()[0].replace(",","") if "Total Area" in x.keys() else np.nan)
        Covered_Area = features_dicts.apply(lambda x: x.get("Covered Area").split()[0].replace(",","") if "Covered Area" in x.keys() else np.nan)
        Description_Len = x["Descriptors"].apply(lambda x:len(" ".join(x)))
        Island = x['Link'].apply(is_island)
        Multiple_Units = x["Link"].apply(lambda x:1 if "units" in x else 0)
        addresses = x["Link"].apply(lambda x:" ".join(x.split("lagos/")[1].split("/")[0:2])).apply(lambda x:re.sub("\d+-[\w-]+","",x))
        address_p1 = []
        address_p2 = []
        for i in addresses:
            address_p1.append(i.split()[0])
            if len(i.split())>1:
                address_p2.append(i.split()[1])
            else:
                address_p2.append(np.nan)
        Area = np.array(address_p1)
        Locality = np.array(address_p2)
        if self.add_extra_features:
            features_kept = ["Listing Title","Latitude/Longitude","Flat","Distance to 3ML","Link"]
            Newly_Built = 1*x["Descriptors"].apply(lambda x:"newly built" in x.lower())
            Pool = 1*x["Descriptors"].apply(lambda x:("pool" in x.lower())|("swimming" in x.lower()))
            Gym = 1*x["Descriptors"].apply(lambda x:"gym" in x.lower())
            Shared  = 1*x["Descriptors"].apply(lambda x:"shared" in x.lower())
            return np.c_[x[features_kept],Area,Locality,Property_Ref,Price,Island,Days_Since_Added,
                     Days_SinceUpdated,Type,Bedrooms,Bathrooms,Toilets,Parking_Spaces,Total_Area,Covered_Area,
                     Serviced,Furnishing,Newly_Built,Pool,Gym,Shared,Multiple_Units,Description_Len]
        else:
            return np.c_[x[features_kept],Area,Locality,Property_Ref,Price,Island,Days_Since_Added,
                     Days_SinceUpdated,Type,Bedrooms,Bathrooms,Toilets,Parking_Spaces,Total_Area,Covered_Area,
                     Serviced,Furnishing,Multiple_Units,Description_Len]

#creating an instance of the transformer
trans = HouseFeatureTransformer(add_extra_features = True)

# setting up the tranformed database 
fk = ["Listing Title","Latitude/Longitude","Flat","Distance to 3ML","Link"]
cols = "Area,Locality,Property_Ref,Price,Island,Days_Since_Added,Days_SinceUpdated,Type,Bedrooms,Bathrooms,Toilets,Parking_Spaces,Total_Area,Covered_Area,Serviced,Furnishing,Newly_Built,Pool,Gym,Shared,Multiple_Units,Description_Len".split(",")
all_cols = fk+cols
df_transformed = pd.DataFrame(trans.fit_transform(df),columns = all_cols)

#np.c_ converts to object type, bringing my numeric columns back to life
numeric_cols = ["Price","Island",'Days_Since_Added','Days_SinceUpdated','Bedrooms', 'Bathrooms', 'Toilets','Serviced',
       'Furnishing', 'Newly_Built', 'Pool', 'Gym', 'Shared',
       'Description_Len',"Distance to 3ML","Total_Area","Covered_Area"]
df_transformed[numeric_cols] = df_transformed[numeric_cols].apply(lambda x:pd.to_numeric(x))

df_transformed.to_pickle(r"C:\Users\Atonye\Documents\Nigeria House Prices Project\pickleddf")
     




import bs4
import requests
import geopy
import pandas as pd
import numpy as np



def create_rawdf(no_pages=100,flats = True):
    ppts_scraped = 0
    last_page = no_pages+1
    if flats:
        link0 = "https://nigeriapropertycentre.com/for-rent/flats-apartments/lagos/showtype?"
        typ = 1
    else:
        link0 = "https://nigeriapropertycentre.com/for-rent/houses/lagos/showtype?"
        typ = 0
    all_properties = []
    for i in range(1,last_page):
        print(f"Page {i} Results")
        link = link0+f"page={i}"
        page = requests.get(link)
        soup = bs4.BeautifulSoup(page.text,"lxml")
        property_links =[]
        page_links = soup.find_all("div",class_="wp-block-body")
        for p in page_links:
            property_links.append("https://nigeriapropertycentre.com/"+p.a["href"])
        for prop in property_links:
            page = requests.get(prop)
            page_soup = bs4.BeautifulSoup(page.text,"lxml")
            try:
                desc = page_soup.find("div",class_="tab-body").find("p")
                desc_list = [i.strip() for i in desc.getText().split("\n") if i!=""]
                other_descriptors = []
                for i in page_soup.find("div",class_="tab-body").find("table").find_all("td"):
                    other_descriptors.append(i.text)
                listing_title = page_soup.find("div",class_="col-sm-8 f15 property-details").find("h4").text
                listing_address = page_soup.find("div",class_="col-sm-8 f15 property-details").find("address").text.replace("\xa0","")
                listing_price = page_soup.find("div",class_="col-sm-4").text
                prop_link = prop
                house_features = [listing_title,listing_price,listing_address,desc_list,other_descriptors,typ,prop_link]
            except:
                house_features = [np.nan for i in range(7)]
            all_properties.append(house_features)
            ppts_scraped +=1
        print("\n")
        # to safeguard against a power outage while running the code, after each page of properties is added a dataframe is saved
        page_df = pd.DataFrame(all_properties,columns = ["Listing Title","Listing Price","Listing Address","Descriptors","Other Features","Flat","Link"])
        page_df.to_csv('prorprties_{}.csv'.format(ppts_scraped))
        
    return pd.DataFrame(all_properties,columns = ["Listing Title","Listing Price","Listing Address","Descriptors","Other Features","Flat","Link"])
            
flats = create_rawdf(flats = True)            
houses = create_rawdf(flats = False)
all_props = flats.append(houses)

#drop all items whith a blank listing title, if any
all_props.drop(all_props[all_props["Listing Title"].isna()].index,inplace=True)


# create function using geopy to geocode listing address
def return_geocodes(x):
    coder = geopy.geocoders.GoogleV3("insert Google Maps API key here")
    all_addresses = []
    for i in x:
        try:
            addy =coder.geocode(i)
            lat = addy.latitude
            lon = addy.longitude
            addy_string = str(lat)+","+str(lon)
            all_addresses.append(addy_string)
        except:
            all_addresses.append(np.nan)
    return all_addresses

# apply return_geocode function to both flats and houses to create a Latitude/ Longitude column
all_props["Latitude/Longitude"] = return_geocodes(all_props["Listing Address"])


# drop items which could not be geocoded if any     
all_props.drop(all_props[all_props["Latitude/Longitude"].isna()].index,inplace=True)

# using bing's distance matrix to get driving distance between the property and third mainland bridge
bing_key = "insert Bing Maps API key here"
origins = []
for i in all_props["Latitude/Longitude"]:
    origin_latitude = float(i.split(",")[0])
    origin_longitude = float(i.split(",")[1])
    dict_origin = {"latitude": origin_latitude,"longitude": origin_longitude }
    origins.append(dict_origin)
        
destination_latitude = 6.5018108
destination_longitude = 3.3999065
destination = [{"latitude":destination_latitude,"longitude":destination_longitude}]
post_json = {'origins':origins,'destinations': destination,'travelMode': "driving"}
params = {'key': bing_key}
r = requests.post('https://dev.virtualearth.net/REST/v1/Routes/DistanceMatrix',params=params, json=post_json)
r_json = r.json()

#parsing results into a list 
distances = []
for i in range(len(all_props)):
    distances.append(r_json["resourceSets"][0]["resources"][0]["results"][i]["travelDistance"])

# creating a new feature - Distance to 3ML
all_props["Distance to 3ML"] = distances

# saving to csv, alternatively save as pickle to stop lists in the data from being turned into strings..
all_props.to_csv("AllProperties.csv")

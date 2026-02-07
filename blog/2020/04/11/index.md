---
title: Estimating how many people live near a landmark / point-of-interest
date: '2020-04-11'
description: 'In this post, I start with a point-of-interest, "Times Square, NYC", and using the Census API I find out how many people live within the census tract that contains this POI (a tract is one of the smallest sub-divisions for which the Census provides population estimates).'
image: social-image.png
options:
  categories:
    - python
---


It can be useful to know how many people live near a landmark / point-of-interest (POI). For example, a location is often considered "walkable" if you can walk to it in 10 minutes or less. Understanding how many people live near a POI is one way of estimating how many people are within walking distance of a POI, if they were to walk from their home to the POI.

In this post, I start with a point-of-interest, "Times Square, NYC", and using the Census API I find out how many people live within the census tract that contains this POI (a tract is one of the smallest sub-divisions for which the Census provides population estimates).

If we wanted to go a bit further down this path of estimating "population within walking distance" we could take this approach and expand it to include all census tracts within a certain distance of our POI census tract. I used this approach one time to understand the potential "reach" of outdoor neighborhood advertising.


```python
from census import Census
from us import states
import censusgeocode as cg
import folium
import geocoder
import pprint
import wget
import zipfile
import shapefile as shp
import pandas as pd
from shapely.geometry import Polygon
import numpy as np

c = Census("MY_API_KEY")
```

# Geocoding the point-of-interest

First we'll geocode our point-of-interest (POI) using `geocoder`. This will give us the latitude and longitude coordinates, among other things.


```python
poi = geocoder.osm('Times Square').json

# Print keys
pprint.pprint(poi.keys())

print("\n" + poi['address'])
```

    dict_keys(['accuracy', 'address', 'bbox', 'city', 'confidence', 'country', 'country_code', 'county', 'icon', 'importance', 'lat', 'lng', 'ok', 'osm_id', 'osm_type', 'place_id', 'place_rank', 'postal', 'quality', 'raw', 'region', 'state', 'status', 'street', 'suburb', 'type'])

    Times Square, West 45th Street, Times Square, Theater District, Manhattan Community Board 5, Manhattan, New York County, New York, 10036, United States of America


Next, we'll use `censusgeocode` to get the geo IDs used by the census. As input, we'll use the latitude and longitude from the previous geocoding.


```python
poi_cg = cg.coordinates(y = poi['lat'], x = poi['lng'])

# Print top-level keys
pprint.pprint(poi_cg.keys())

# Print Census Tract keys
pprint.pprint(poi_cg['Census Tracts'][0].keys())
```

    dict_keys(['2010 Census Blocks', 'States', 'Counties', 'Census Tracts'])
    dict_keys(['GEOID', 'CENTLAT', 'AREAWATER', 'STATE', 'BASENAME', 'OID', 'LSADC', 'FUNCSTAT', 'INTPTLAT', 'NAME', 'OBJECTID', 'TRACT', 'CENTLON', 'AREALAND', 'INTPTLON', 'MTFCC', 'COUNTY', 'CENT', 'INTPT'])


# Mapping the tract

First we'll find the shapefiles for NY state tracts using the `us` library.

## Getting shapefiles


```python
shpurls = states.NY.shapefile_urls()
for region, url in shpurls.items():
    print(region, url)
```

    tract https://www2.census.gov/geo/tiger/TIGER2010/TRACT/2010/tl_2010_36_tract10.zip
    cd https://www2.census.gov/geo/tiger/TIGER2010/CD/111/tl_2010_36_cd111.zip
    county https://www2.census.gov/geo/tiger/TIGER2010/COUNTY/2010/tl_2010_36_county10.zip
    state https://www2.census.gov/geo/tiger/TIGER2010/STATE/2010/tl_2010_36_state10.zip
    zcta https://www2.census.gov/geo/tiger/TIGER2010/ZCTA5/2010/tl_2010_36_zcta510.zip
    block https://www2.census.gov/geo/tiger/TIGER2010/TABBLOCK/2010/tl_2010_36_tabblock10.zip
    blockgroup https://www2.census.gov/geo/tiger/TIGER2010/BG/2010/tl_2010_36_bg10.zip


Now we'll download and unzip the shapefiles for the tract zip.


```python
wget.download('https://www2.census.gov/geo/tiger/TIGER2010/TRACT/2010/tl_2010_36_tract10.zip')
with zipfile.ZipFile('tl_2010_36_tract10.zip', 'r') as zip_ref:
    zip_ref.extractall()
```

    -1 / unknown

## Converting shapefile to LNG/LAT coords

Next, we'll read the shape files into a dataframe, giving us a "coords" column, using the `shapefile` library. Note that these will be in LNG, LAT (not LAT, LNG).


```python
def read_shapefile(sf):
    """
    Read a shapefile into a Pandas dataframe with a 'coords'
    column holding the geometry information. This uses the pyshp
    package
    """
    fields = [x[0] for x in sf.fields][1:]
    records = sf.records()
    shps = [s.points for s in sf.shapes()]
    df = pd.DataFrame(columns=fields, data=records)
    df = df.assign(coords=shps)
    return df

shp_path = 'tl_2010_36_tract10.shp'
sf = shp.Reader(shp_path)
df = read_shapefile(sf)
```

This is the tract we're interested in:


```python
poi_tract = df[df['GEOID10'] == poi_cg['Census Tracts'][0]['GEOID']].reset_index()
poi_tract['coords']
```




    0    [(-73.985085, 40.758589), (-73.98225599999999,...
    Name: coords, dtype: object



## Map the POI marker and tract polygon

Finally, we're ready to map the POI and the tract polygon in which it is located. We'll use `shapely` to get the polygon and `folium` to do the mapping.


```python
# Convert to Polygon
poi_poly = Polygon(poi_tract['coords'][0])

# Initialize map with zoom and custom tileset, centered on POI
m = folium.Map(location=[poi['lat'], poi['lng']],
               zoom_start=16,
               tiles='cartodbpositron')

# Add a map pin
folium.Marker([poi['lat'], poi['lng']]).add_to(m)

# Add the polygon
folium.GeoJson(poi_poly).add_to(m)

m
```




<div style="width:100%;"><div style="position:relative;width:100%;height:0;padding-bottom:60%;"><iframe src="about:blank" style="position:absolute;width:100%;height:100%;left:0;top:0;border:none !important;" data-html=PCFET0NUWVBFIGh0bWw+CjxoZWFkPiAgICAKICAgIDxtZXRhIGh0dHAtZXF1aXY9ImNvbnRlbnQtdHlwZSIgY29udGVudD0idGV4dC9odG1sOyBjaGFyc2V0PVVURi04IiAvPgogICAgCiAgICAgICAgPHNjcmlwdD4KICAgICAgICAgICAgTF9OT19UT1VDSCA9IGZhbHNlOwogICAgICAgICAgICBMX0RJU0FCTEVfM0QgPSBmYWxzZTsKICAgICAgICA8L3NjcmlwdD4KICAgIAogICAgPHNjcmlwdCBzcmM9Imh0dHBzOi8vY2RuLmpzZGVsaXZyLm5ldC9ucG0vbGVhZmxldEAxLjUuMS9kaXN0L2xlYWZsZXQuanMiPjwvc2NyaXB0PgogICAgPHNjcmlwdCBzcmM9Imh0dHBzOi8vY29kZS5qcXVlcnkuY29tL2pxdWVyeS0xLjEyLjQubWluLmpzIj48L3NjcmlwdD4KICAgIDxzY3JpcHQgc3JjPSJodHRwczovL21heGNkbi5ib290c3RyYXBjZG4uY29tL2Jvb3RzdHJhcC8zLjIuMC9qcy9ib290c3RyYXAubWluLmpzIj48L3NjcmlwdD4KICAgIDxzY3JpcHQgc3JjPSJodHRwczovL2NkbmpzLmNsb3VkZmxhcmUuY29tL2FqYXgvbGlicy9MZWFmbGV0LmF3ZXNvbWUtbWFya2Vycy8yLjAuMi9sZWFmbGV0LmF3ZXNvbWUtbWFya2Vycy5qcyI+PC9zY3JpcHQ+CiAgICA8bGluayByZWw9InN0eWxlc2hlZXQiIGhyZWY9Imh0dHBzOi8vY2RuLmpzZGVsaXZyLm5ldC9ucG0vbGVhZmxldEAxLjUuMS9kaXN0L2xlYWZsZXQuY3NzIi8+CiAgICA8bGluayByZWw9InN0eWxlc2hlZXQiIGhyZWY9Imh0dHBzOi8vbWF4Y2RuLmJvb3RzdHJhcGNkbi5jb20vYm9vdHN0cmFwLzMuMi4wL2Nzcy9ib290c3RyYXAubWluLmNzcyIvPgogICAgPGxpbmsgcmVsPSJzdHlsZXNoZWV0IiBocmVmPSJodHRwczovL21heGNkbi5ib290c3RyYXBjZG4uY29tL2Jvb3RzdHJhcC8zLjIuMC9jc3MvYm9vdHN0cmFwLXRoZW1lLm1pbi5jc3MiLz4KICAgIDxsaW5rIHJlbD0ic3R5bGVzaGVldCIgaHJlZj0iaHR0cHM6Ly9tYXhjZG4uYm9vdHN0cmFwY2RuLmNvbS9mb250LWF3ZXNvbWUvNC42LjMvY3NzL2ZvbnQtYXdlc29tZS5taW4uY3NzIi8+CiAgICA8bGluayByZWw9InN0eWxlc2hlZXQiIGhyZWY9Imh0dHBzOi8vY2RuanMuY2xvdWRmbGFyZS5jb20vYWpheC9saWJzL0xlYWZsZXQuYXdlc29tZS1tYXJrZXJzLzIuMC4yL2xlYWZsZXQuYXdlc29tZS1tYXJrZXJzLmNzcyIvPgogICAgPGxpbmsgcmVsPSJzdHlsZXNoZWV0IiBocmVmPSJodHRwczovL3Jhd2Nkbi5naXRoYWNrLmNvbS9weXRob24tdmlzdWFsaXphdGlvbi9mb2xpdW0vbWFzdGVyL2ZvbGl1bS90ZW1wbGF0ZXMvbGVhZmxldC5hd2Vzb21lLnJvdGF0ZS5jc3MiLz4KICAgIDxzdHlsZT5odG1sLCBib2R5IHt3aWR0aDogMTAwJTtoZWlnaHQ6IDEwMCU7bWFyZ2luOiAwO3BhZGRpbmc6IDA7fTwvc3R5bGU+CiAgICA8c3R5bGU+I21hcCB7cG9zaXRpb246YWJzb2x1dGU7dG9wOjA7Ym90dG9tOjA7cmlnaHQ6MDtsZWZ0OjA7fTwvc3R5bGU+CiAgICAKICAgICAgICAgICAgPG1ldGEgbmFtZT0idmlld3BvcnQiIGNvbnRlbnQ9IndpZHRoPWRldmljZS13aWR0aCwKICAgICAgICAgICAgICAgIGluaXRpYWwtc2NhbGU9MS4wLCBtYXhpbXVtLXNjYWxlPTEuMCwgdXNlci1zY2FsYWJsZT1ubyIgLz4KICAgICAgICAgICAgPHN0eWxlPgogICAgICAgICAgICAgICAgI21hcF9kMjlmZWY4ZWIxOTc0YzRlOGJlMzRmMDNhNWNlY2Q4MyB7CiAgICAgICAgICAgICAgICAgICAgcG9zaXRpb246IHJlbGF0aXZlOwogICAgICAgICAgICAgICAgICAgIHdpZHRoOiAxMDAuMCU7CiAgICAgICAgICAgICAgICAgICAgaGVpZ2h0OiAxMDAuMCU7CiAgICAgICAgICAgICAgICAgICAgbGVmdDogMC4wJTsKICAgICAgICAgICAgICAgICAgICB0b3A6IDAuMCU7CiAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgIDwvc3R5bGU+CiAgICAgICAgCjwvaGVhZD4KPGJvZHk+ICAgIAogICAgCiAgICAgICAgICAgIDxkaXYgY2xhc3M9ImZvbGl1bS1tYXAiIGlkPSJtYXBfZDI5ZmVmOGViMTk3NGM0ZThiZTM0ZjAzYTVjZWNkODMiID48L2Rpdj4KICAgICAgICAKPC9ib2R5Pgo8c2NyaXB0PiAgICAKICAgIAogICAgICAgICAgICB2YXIgbWFwX2QyOWZlZjhlYjE5NzRjNGU4YmUzNGYwM2E1Y2VjZDgzID0gTC5tYXAoCiAgICAgICAgICAgICAgICAibWFwX2QyOWZlZjhlYjE5NzRjNGU4YmUzNGYwM2E1Y2VjZDgzIiwKICAgICAgICAgICAgICAgIHsKICAgICAgICAgICAgICAgICAgICBjZW50ZXI6IFs0MC43NTcyODA1NTAwMDAwMDQsIC03My45ODU4NTUwMzU0NTkxN10sCiAgICAgICAgICAgICAgICAgICAgY3JzOiBMLkNSUy5FUFNHMzg1NywKICAgICAgICAgICAgICAgICAgICB6b29tOiAxNiwKICAgICAgICAgICAgICAgICAgICB6b29tQ29udHJvbDogdHJ1ZSwKICAgICAgICAgICAgICAgICAgICBwcmVmZXJDYW52YXM6IGZhbHNlLAogICAgICAgICAgICAgICAgfQogICAgICAgICAgICApOwoKICAgICAgICAgICAgCgogICAgICAgIAogICAgCiAgICAgICAgICAgIHZhciB0aWxlX2xheWVyX2I5MTc0ZWE0MTBkNjRhMzQ4NWU0MzkxY2U3YzA3MTVjID0gTC50aWxlTGF5ZXIoCiAgICAgICAgICAgICAgICAiaHR0cHM6Ly9jYXJ0b2RiLWJhc2VtYXBzLXtzfS5nbG9iYWwuc3NsLmZhc3RseS5uZXQvbGlnaHRfYWxsL3t6fS97eH0ve3l9LnBuZyIsCiAgICAgICAgICAgICAgICB7ImF0dHJpYnV0aW9uIjogIlx1MDAyNmNvcHk7IFx1MDAzY2EgaHJlZj1cImh0dHA6Ly93d3cub3BlbnN0cmVldG1hcC5vcmcvY29weXJpZ2h0XCJcdTAwM2VPcGVuU3RyZWV0TWFwXHUwMDNjL2FcdTAwM2UgY29udHJpYnV0b3JzIFx1MDAyNmNvcHk7IFx1MDAzY2EgaHJlZj1cImh0dHA6Ly9jYXJ0b2RiLmNvbS9hdHRyaWJ1dGlvbnNcIlx1MDAzZUNhcnRvREJcdTAwM2MvYVx1MDAzZSwgQ2FydG9EQiBcdTAwM2NhIGhyZWYgPVwiaHR0cDovL2NhcnRvZGIuY29tL2F0dHJpYnV0aW9uc1wiXHUwMDNlYXR0cmlidXRpb25zXHUwMDNjL2FcdTAwM2UiLCAiZGV0ZWN0UmV0aW5hIjogZmFsc2UsICJtYXhOYXRpdmVab29tIjogMTgsICJtYXhab29tIjogMTgsICJtaW5ab29tIjogMCwgIm5vV3JhcCI6IGZhbHNlLCAib3BhY2l0eSI6IDEsICJzdWJkb21haW5zIjogImFiYyIsICJ0bXMiOiBmYWxzZX0KICAgICAgICAgICAgKS5hZGRUbyhtYXBfZDI5ZmVmOGViMTk3NGM0ZThiZTM0ZjAzYTVjZWNkODMpOwogICAgICAgIAogICAgCiAgICAgICAgICAgIHZhciBtYXJrZXJfZDI4YzFkZDMwYmM2NDc0YjljOTFiYTc0ZGY3NDgzOTcgPSBMLm1hcmtlcigKICAgICAgICAgICAgICAgIFs0MC43NTcyODA1NTAwMDAwMDQsIC03My45ODU4NTUwMzU0NTkxN10sCiAgICAgICAgICAgICAgICB7fQogICAgICAgICAgICApLmFkZFRvKG1hcF9kMjlmZWY4ZWIxOTc0YzRlOGJlMzRmMDNhNWNlY2Q4Myk7CiAgICAgICAgCiAgICAKICAgICAgICBmdW5jdGlvbiBnZW9fanNvbl9hOTcyNzZjOTdkYTk0YmM3YTBjYTQ1YWM1ODY0N2JiZF9vbkVhY2hGZWF0dXJlKGZlYXR1cmUsIGxheWVyKSB7CiAgICAgICAgICAgIGxheWVyLm9uKHsKICAgICAgICAgICAgICAgIGNsaWNrOiBmdW5jdGlvbihlKSB7CiAgICAgICAgICAgICAgICAgICAgbWFwX2QyOWZlZjhlYjE5NzRjNGU4YmUzNGYwM2E1Y2VjZDgzLmZpdEJvdW5kcyhlLnRhcmdldC5nZXRCb3VuZHMoKSk7CiAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgIH0pOwogICAgICAgIH07CiAgICAgICAgdmFyIGdlb19qc29uX2E5NzI3NmM5N2RhOTRiYzdhMGNhNDVhYzU4NjQ3YmJkID0gTC5nZW9Kc29uKG51bGwsIHsKICAgICAgICAgICAgICAgIG9uRWFjaEZlYXR1cmU6IGdlb19qc29uX2E5NzI3NmM5N2RhOTRiYzdhMGNhNDVhYzU4NjQ3YmJkX29uRWFjaEZlYXR1cmUsCiAgICAgICAgICAgIAogICAgICAgIH0pOwogICAgICAgIGZ1bmN0aW9uIGdlb19qc29uX2E5NzI3NmM5N2RhOTRiYzdhMGNhNDVhYzU4NjQ3YmJkX2FkZCAoZGF0YSkgewogICAgICAgICAgICBnZW9fanNvbl9hOTcyNzZjOTdkYTk0YmM3YTBjYTQ1YWM1ODY0N2JiZC5hZGREYXRhKGRhdGEpCiAgICAgICAgICAgICAgICAuYWRkVG8obWFwX2QyOWZlZjhlYjE5NzRjNGU4YmUzNGYwM2E1Y2VjZDgzKTsKICAgICAgICB9CiAgICAgICAgICAgIGdlb19qc29uX2E5NzI3NmM5N2RhOTRiYzdhMGNhNDVhYzU4NjQ3YmJkX2FkZCh7ImNvb3JkaW5hdGVzIjogW1tbLTczLjk4NTA4NSwgNDAuNzU4NTg5XSwgWy03My45ODIyNTU5OTk5OTk5OSwgNDAuNzU3Mzg3XSwgWy03My45ODI3MTE5OTk5OTk5OSwgNDAuNzU2NzcxXSwgWy03My45ODMxNjc5OTk5OTk5OSwgNDAuNzU2MTM5OTk5OTk5OTk1XSwgWy03My45ODM2MjM5OTk5OTk5OSwgNDAuNzU1NTE2XSwgWy03My45ODQxMTgsIDQwLjc1NDg0Ml0sIFstNzMuOTg2Mzk4LCA0MC43NTU4MDRdLCBbLTczLjk4Njk0OSwgNDAuNzU2MDM2XSwgWy03My45ODk3OTEsIDQwLjc1NzIzNF0sIFstNzMuOTg5Mjk3LCA0MC43NTc5MDY5OTk5OTk5OTZdLCBbLTczLjk4ODg0MTk5OTk5OTk5LCA0MC43NTg1MzNdLCBbLTczLjk4ODM5MSwgNDAuNzU5MTY0XSwgWy03My45ODc5MjcsIDQwLjc1OTc5MV0sIFstNzMuOTg1MzIyLCA0MC43NTg2ODY5OTk5OTk5OTVdLCBbLTczLjk4NTA4NSwgNDAuNzU4NTg5XV1dLCAidHlwZSI6ICJQb2x5Z29uIn0pOwogICAgICAgIAo8L3NjcmlwdD4= onload="this.contentDocument.open();this.contentDocument.write(atob(this.getAttribute('data-html')));this.contentDocument.close();" allowfullscreen webkitallowfullscreen mozallowfullscreen></iframe></div></div>



# Population for census tract

Now, the last step is finding the population for this census tract.

The variable we are interested in is `B01003_001E`, an estimate of the total population. A full list of the variable codes and definitions can be found at the [ACS developer page](https://www.census.gov/data/developers/data-sets/acs-5year.html) (see the "2018 ACS Detailed Tables Variables").


```python
poi_pop = c.acs5.state_county_tract(('NAME', 'B01003_001E'),
                                     poi_cg['Census Tracts'][0]['STATE'],
                                     poi_cg['Census Tracts'][0]['COUNTY'],
                                     poi_cg['Census Tracts'][0]['TRACT'])

poi_pop_str = str(round(poi_pop[0]['B01003_001E']))

poi_pop_str
```




    '1027'




```python
folium.Marker(
    [poi['lat'], poi['lng']],
    icon=folium.DivIcon(
        icon_size=(150, 36),
        icon_anchor=(0, 0),
        html='<div style="font-size: 10pt;\
                          background:white;\
                          padding:5px;\
                          border:1px solid red">\
                          The population in the census tract\
                          containing Times Square is ' + poi_pop_str + '\
              </div>',
        )
    ).add_to(m)

m
```




<div style="width:100%;"><div style="position:relative;width:100%;height:0;padding-bottom:60%;"><iframe src="about:blank" style="position:absolute;width:100%;height:100%;left:0;top:0;border:none !important;" data-html=PCFET0NUWVBFIGh0bWw+CjxoZWFkPiAgICAKICAgIDxtZXRhIGh0dHAtZXF1aXY9ImNvbnRlbnQtdHlwZSIgY29udGVudD0idGV4dC9odG1sOyBjaGFyc2V0PVVURi04IiAvPgogICAgCiAgICAgICAgPHNjcmlwdD4KICAgICAgICAgICAgTF9OT19UT1VDSCA9IGZhbHNlOwogICAgICAgICAgICBMX0RJU0FCTEVfM0QgPSBmYWxzZTsKICAgICAgICA8L3NjcmlwdD4KICAgIAogICAgPHNjcmlwdCBzcmM9Imh0dHBzOi8vY2RuLmpzZGVsaXZyLm5ldC9ucG0vbGVhZmxldEAxLjUuMS9kaXN0L2xlYWZsZXQuanMiPjwvc2NyaXB0PgogICAgPHNjcmlwdCBzcmM9Imh0dHBzOi8vY29kZS5qcXVlcnkuY29tL2pxdWVyeS0xLjEyLjQubWluLmpzIj48L3NjcmlwdD4KICAgIDxzY3JpcHQgc3JjPSJodHRwczovL21heGNkbi5ib290c3RyYXBjZG4uY29tL2Jvb3RzdHJhcC8zLjIuMC9qcy9ib290c3RyYXAubWluLmpzIj48L3NjcmlwdD4KICAgIDxzY3JpcHQgc3JjPSJodHRwczovL2NkbmpzLmNsb3VkZmxhcmUuY29tL2FqYXgvbGlicy9MZWFmbGV0LmF3ZXNvbWUtbWFya2Vycy8yLjAuMi9sZWFmbGV0LmF3ZXNvbWUtbWFya2Vycy5qcyI+PC9zY3JpcHQ+CiAgICA8bGluayByZWw9InN0eWxlc2hlZXQiIGhyZWY9Imh0dHBzOi8vY2RuLmpzZGVsaXZyLm5ldC9ucG0vbGVhZmxldEAxLjUuMS9kaXN0L2xlYWZsZXQuY3NzIi8+CiAgICA8bGluayByZWw9InN0eWxlc2hlZXQiIGhyZWY9Imh0dHBzOi8vbWF4Y2RuLmJvb3RzdHJhcGNkbi5jb20vYm9vdHN0cmFwLzMuMi4wL2Nzcy9ib290c3RyYXAubWluLmNzcyIvPgogICAgPGxpbmsgcmVsPSJzdHlsZXNoZWV0IiBocmVmPSJodHRwczovL21heGNkbi5ib290c3RyYXBjZG4uY29tL2Jvb3RzdHJhcC8zLjIuMC9jc3MvYm9vdHN0cmFwLXRoZW1lLm1pbi5jc3MiLz4KICAgIDxsaW5rIHJlbD0ic3R5bGVzaGVldCIgaHJlZj0iaHR0cHM6Ly9tYXhjZG4uYm9vdHN0cmFwY2RuLmNvbS9mb250LWF3ZXNvbWUvNC42LjMvY3NzL2ZvbnQtYXdlc29tZS5taW4uY3NzIi8+CiAgICA8bGluayByZWw9InN0eWxlc2hlZXQiIGhyZWY9Imh0dHBzOi8vY2RuanMuY2xvdWRmbGFyZS5jb20vYWpheC9saWJzL0xlYWZsZXQuYXdlc29tZS1tYXJrZXJzLzIuMC4yL2xlYWZsZXQuYXdlc29tZS1tYXJrZXJzLmNzcyIvPgogICAgPGxpbmsgcmVsPSJzdHlsZXNoZWV0IiBocmVmPSJodHRwczovL3Jhd2Nkbi5naXRoYWNrLmNvbS9weXRob24tdmlzdWFsaXphdGlvbi9mb2xpdW0vbWFzdGVyL2ZvbGl1bS90ZW1wbGF0ZXMvbGVhZmxldC5hd2Vzb21lLnJvdGF0ZS5jc3MiLz4KICAgIDxzdHlsZT5odG1sLCBib2R5IHt3aWR0aDogMTAwJTtoZWlnaHQ6IDEwMCU7bWFyZ2luOiAwO3BhZGRpbmc6IDA7fTwvc3R5bGU+CiAgICA8c3R5bGU+I21hcCB7cG9zaXRpb246YWJzb2x1dGU7dG9wOjA7Ym90dG9tOjA7cmlnaHQ6MDtsZWZ0OjA7fTwvc3R5bGU+CiAgICAKICAgICAgICAgICAgPG1ldGEgbmFtZT0idmlld3BvcnQiIGNvbnRlbnQ9IndpZHRoPWRldmljZS13aWR0aCwKICAgICAgICAgICAgICAgIGluaXRpYWwtc2NhbGU9MS4wLCBtYXhpbXVtLXNjYWxlPTEuMCwgdXNlci1zY2FsYWJsZT1ubyIgLz4KICAgICAgICAgICAgPHN0eWxlPgogICAgICAgICAgICAgICAgI21hcF9kMjlmZWY4ZWIxOTc0YzRlOGJlMzRmMDNhNWNlY2Q4MyB7CiAgICAgICAgICAgICAgICAgICAgcG9zaXRpb246IHJlbGF0aXZlOwogICAgICAgICAgICAgICAgICAgIHdpZHRoOiAxMDAuMCU7CiAgICAgICAgICAgICAgICAgICAgaGVpZ2h0OiAxMDAuMCU7CiAgICAgICAgICAgICAgICAgICAgbGVmdDogMC4wJTsKICAgICAgICAgICAgICAgICAgICB0b3A6IDAuMCU7CiAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgIDwvc3R5bGU+CiAgICAgICAgCjwvaGVhZD4KPGJvZHk+ICAgIAogICAgCiAgICAgICAgICAgIDxkaXYgY2xhc3M9ImZvbGl1bS1tYXAiIGlkPSJtYXBfZDI5ZmVmOGViMTk3NGM0ZThiZTM0ZjAzYTVjZWNkODMiID48L2Rpdj4KICAgICAgICAKPC9ib2R5Pgo8c2NyaXB0PiAgICAKICAgIAogICAgICAgICAgICB2YXIgbWFwX2QyOWZlZjhlYjE5NzRjNGU4YmUzNGYwM2E1Y2VjZDgzID0gTC5tYXAoCiAgICAgICAgICAgICAgICAibWFwX2QyOWZlZjhlYjE5NzRjNGU4YmUzNGYwM2E1Y2VjZDgzIiwKICAgICAgICAgICAgICAgIHsKICAgICAgICAgICAgICAgICAgICBjZW50ZXI6IFs0MC43NTcyODA1NTAwMDAwMDQsIC03My45ODU4NTUwMzU0NTkxN10sCiAgICAgICAgICAgICAgICAgICAgY3JzOiBMLkNSUy5FUFNHMzg1NywKICAgICAgICAgICAgICAgICAgICB6b29tOiAxNiwKICAgICAgICAgICAgICAgICAgICB6b29tQ29udHJvbDogdHJ1ZSwKICAgICAgICAgICAgICAgICAgICBwcmVmZXJDYW52YXM6IGZhbHNlLAogICAgICAgICAgICAgICAgfQogICAgICAgICAgICApOwoKICAgICAgICAgICAgCgogICAgICAgIAogICAgCiAgICAgICAgICAgIHZhciB0aWxlX2xheWVyX2I5MTc0ZWE0MTBkNjRhMzQ4NWU0MzkxY2U3YzA3MTVjID0gTC50aWxlTGF5ZXIoCiAgICAgICAgICAgICAgICAiaHR0cHM6Ly9jYXJ0b2RiLWJhc2VtYXBzLXtzfS5nbG9iYWwuc3NsLmZhc3RseS5uZXQvbGlnaHRfYWxsL3t6fS97eH0ve3l9LnBuZyIsCiAgICAgICAgICAgICAgICB7ImF0dHJpYnV0aW9uIjogIlx1MDAyNmNvcHk7IFx1MDAzY2EgaHJlZj1cImh0dHA6Ly93d3cub3BlbnN0cmVldG1hcC5vcmcvY29weXJpZ2h0XCJcdTAwM2VPcGVuU3RyZWV0TWFwXHUwMDNjL2FcdTAwM2UgY29udHJpYnV0b3JzIFx1MDAyNmNvcHk7IFx1MDAzY2EgaHJlZj1cImh0dHA6Ly9jYXJ0b2RiLmNvbS9hdHRyaWJ1dGlvbnNcIlx1MDAzZUNhcnRvREJcdTAwM2MvYVx1MDAzZSwgQ2FydG9EQiBcdTAwM2NhIGhyZWYgPVwiaHR0cDovL2NhcnRvZGIuY29tL2F0dHJpYnV0aW9uc1wiXHUwMDNlYXR0cmlidXRpb25zXHUwMDNjL2FcdTAwM2UiLCAiZGV0ZWN0UmV0aW5hIjogZmFsc2UsICJtYXhOYXRpdmVab29tIjogMTgsICJtYXhab29tIjogMTgsICJtaW5ab29tIjogMCwgIm5vV3JhcCI6IGZhbHNlLCAib3BhY2l0eSI6IDEsICJzdWJkb21haW5zIjogImFiYyIsICJ0bXMiOiBmYWxzZX0KICAgICAgICAgICAgKS5hZGRUbyhtYXBfZDI5ZmVmOGViMTk3NGM0ZThiZTM0ZjAzYTVjZWNkODMpOwogICAgICAgIAogICAgCiAgICAgICAgICAgIHZhciBtYXJrZXJfZDI4YzFkZDMwYmM2NDc0YjljOTFiYTc0ZGY3NDgzOTcgPSBMLm1hcmtlcigKICAgICAgICAgICAgICAgIFs0MC43NTcyODA1NTAwMDAwMDQsIC03My45ODU4NTUwMzU0NTkxN10sCiAgICAgICAgICAgICAgICB7fQogICAgICAgICAgICApLmFkZFRvKG1hcF9kMjlmZWY4ZWIxOTc0YzRlOGJlMzRmMDNhNWNlY2Q4Myk7CiAgICAgICAgCiAgICAKICAgICAgICBmdW5jdGlvbiBnZW9fanNvbl9hOTcyNzZjOTdkYTk0YmM3YTBjYTQ1YWM1ODY0N2JiZF9vbkVhY2hGZWF0dXJlKGZlYXR1cmUsIGxheWVyKSB7CiAgICAgICAgICAgIGxheWVyLm9uKHsKICAgICAgICAgICAgICAgIGNsaWNrOiBmdW5jdGlvbihlKSB7CiAgICAgICAgICAgICAgICAgICAgbWFwX2QyOWZlZjhlYjE5NzRjNGU4YmUzNGYwM2E1Y2VjZDgzLmZpdEJvdW5kcyhlLnRhcmdldC5nZXRCb3VuZHMoKSk7CiAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgIH0pOwogICAgICAgIH07CiAgICAgICAgdmFyIGdlb19qc29uX2E5NzI3NmM5N2RhOTRiYzdhMGNhNDVhYzU4NjQ3YmJkID0gTC5nZW9Kc29uKG51bGwsIHsKICAgICAgICAgICAgICAgIG9uRWFjaEZlYXR1cmU6IGdlb19qc29uX2E5NzI3NmM5N2RhOTRiYzdhMGNhNDVhYzU4NjQ3YmJkX29uRWFjaEZlYXR1cmUsCiAgICAgICAgICAgIAogICAgICAgIH0pOwogICAgICAgIGZ1bmN0aW9uIGdlb19qc29uX2E5NzI3NmM5N2RhOTRiYzdhMGNhNDVhYzU4NjQ3YmJkX2FkZCAoZGF0YSkgewogICAgICAgICAgICBnZW9fanNvbl9hOTcyNzZjOTdkYTk0YmM3YTBjYTQ1YWM1ODY0N2JiZC5hZGREYXRhKGRhdGEpCiAgICAgICAgICAgICAgICAuYWRkVG8obWFwX2QyOWZlZjhlYjE5NzRjNGU4YmUzNGYwM2E1Y2VjZDgzKTsKICAgICAgICB9CiAgICAgICAgICAgIGdlb19qc29uX2E5NzI3NmM5N2RhOTRiYzdhMGNhNDVhYzU4NjQ3YmJkX2FkZCh7ImNvb3JkaW5hdGVzIjogW1tbLTczLjk4NTA4NSwgNDAuNzU4NTg5XSwgWy03My45ODIyNTU5OTk5OTk5OSwgNDAuNzU3Mzg3XSwgWy03My45ODI3MTE5OTk5OTk5OSwgNDAuNzU2NzcxXSwgWy03My45ODMxNjc5OTk5OTk5OSwgNDAuNzU2MTM5OTk5OTk5OTk1XSwgWy03My45ODM2MjM5OTk5OTk5OSwgNDAuNzU1NTE2XSwgWy03My45ODQxMTgsIDQwLjc1NDg0Ml0sIFstNzMuOTg2Mzk4LCA0MC43NTU4MDRdLCBbLTczLjk4Njk0OSwgNDAuNzU2MDM2XSwgWy03My45ODk3OTEsIDQwLjc1NzIzNF0sIFstNzMuOTg5Mjk3LCA0MC43NTc5MDY5OTk5OTk5OTZdLCBbLTczLjk4ODg0MTk5OTk5OTk5LCA0MC43NTg1MzNdLCBbLTczLjk4ODM5MSwgNDAuNzU5MTY0XSwgWy03My45ODc5MjcsIDQwLjc1OTc5MV0sIFstNzMuOTg1MzIyLCA0MC43NTg2ODY5OTk5OTk5OTVdLCBbLTczLjk4NTA4NSwgNDAuNzU4NTg5XV1dLCAidHlwZSI6ICJQb2x5Z29uIn0pOwogICAgICAgIAogICAgCiAgICAgICAgICAgIHZhciBtYXJrZXJfZTI1NTgyYjE1ZDY2NDZkY2E1OGNlMWI3YTQ4N2Q4ZTEgPSBMLm1hcmtlcigKICAgICAgICAgICAgICAgIFs0MC43NTcyODA1NTAwMDAwMDQsIC03My45ODU4NTUwMzU0NTkxN10sCiAgICAgICAgICAgICAgICB7fQogICAgICAgICAgICApLmFkZFRvKG1hcF9kMjlmZWY4ZWIxOTc0YzRlOGJlMzRmMDNhNWNlY2Q4Myk7CiAgICAgICAgCiAgICAKICAgICAgICAgICAgdmFyIGRpdl9pY29uX2Y5MDY3OTYyN2VlYzRhYzg5ZmZmMTYyODhhNzAzYWQ1ID0gTC5kaXZJY29uKHsiY2xhc3NOYW1lIjogImVtcHR5IiwgImh0bWwiOiAiXHUwMDNjZGl2IHN0eWxlPVwiZm9udC1zaXplOiAxMHB0OyAgICAgICAgICAgICAgICAgICAgICAgICAgYmFja2dyb3VuZDp3aGl0ZTsgICAgICAgICAgICAgICAgICAgICAgICAgIHBhZGRpbmc6NXB4OyAgICAgICAgICAgICAgICAgICAgICAgICAgYm9yZGVyOjFweCBzb2xpZCByZWRcIlx1MDAzZSAgICAgICAgICAgICAgICAgICAgICAgICAgVGhlIHBvcHVsYXRpb24gaW4gdGhlIGNlbnN1cyB0cmFjdCAgICAgICAgICAgICAgICAgICAgICAgICAgY29udGFpbmluZyBUaW1lcyBTcXVhcmUgaXMgMTAyNyAgICAgICAgICAgICAgXHUwMDNjL2Rpdlx1MDAzZSIsICJpY29uQW5jaG9yIjogWzAsIDBdLCAiaWNvblNpemUiOiBbMTUwLCAzNl19KTsKICAgICAgICAgICAgbWFya2VyX2UyNTU4MmIxNWQ2NjQ2ZGNhNThjZTFiN2E0ODdkOGUxLnNldEljb24oZGl2X2ljb25fZjkwNjc5NjI3ZWVjNGFjODlmZmYxNjI4OGE3MDNhZDUpOwogICAgICAgIAo8L3NjcmlwdD4= onload="this.contentDocument.open();this.contentDocument.write(atob(this.getAttribute('data-html')));this.contentDocument.close();" allowfullscreen webkitallowfullscreen mozallowfullscreen></iframe></div></div>


<script src="https://giscus.app/client.js"
        data-repo="tylerburleigh/tylerburleigh.github.io"
        data-repo-id="R_kgDOKMo8ww"
        data-category="Blog comments"
        data-category-id="DIC_kwDOIg6EJc4CSz92"
        data-mapping="pathname"
        data-strict="0"
        data-reactions-enabled="1"
        data-emit-metadata="0"
        data-input-position="bottom"
        data-theme="light"
        data-lang="en"
        crossorigin="anonymous"
        async>
</script>

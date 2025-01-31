from pathlib import Path
import geopandas as gpd

"https://geoappext.nrcan.gc.ca/arcgis/rest/services/IETS/PCWIS/MapServer/1/query?where=1%3D1&text=&objectIds=1&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&having=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&historicMoment=&returnDistinctValues=false&resultOffset=&resultRecordCount=&queryByDistance=&returnExtentOnly=false&datumTransformation=&parameterValues=&rangeValues=&quantizationParameters=&f=html"

path = Path("data/wind_turbine_database_en.gdb/")

gdf = gpd.read_file(path)
gdf_quebec = gdf[gdf['province_territory'] == 'Quebec']


project_names = gdf_quebec['project_name']
project_names = set([name for name in project_names if name is not None])


# Define the parameters for the query
params = {
    "where": "project_name = 'Your Windmill Project Name'",
    "outFields": "Wind_speed",
    "returnGeometry": False,
    "f": "json"
}
geoappext.nrcan.gc.ca
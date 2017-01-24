#!/usr/bin/python
#coding: utf-8
# Niels Debonne - created 23-02-2017
# Make cost image and accessibility map for Cambodia
# cost is dependent on TRI and Road type / availability and water

# Setting the data sources and libraries
print 'starting up'
import arcpy
arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = 1
# set working directory and paths to road map rasters, and Terrain Ruggedness Index

# roads shapefile having 3 classes: primary road (1), secondary road (2) and <unknown> (3)
roads = r'C:\Users\nde370\surfdrive\storage\GeoData\Processing\Intermediate\accessibility\KHM_rds_Diva\KHM_roads.shp'

# Terrain Ruggedness ranges between 0 and 49 m/m. classify according to user settings in three classes: smooth, rugged and very rugged
TRI = r'C:\Users\nde370\surfdrive\storage\GeoData\Finals\FinalFactorsAsTifsWithMetadata\TRI_SRTM_Cambodia.tif'

# water bodies: this has a field called cost which we can update.
water = r'C:\Users\nde370\surfdrive\storage\GeoData\RetrievedData\water-bodies-09-08-2016_ODC\water-bodies.shp'

# target raster will be used to set cell size, projection, extent
print 'retrieving raster specifications'
target = r'C:\Users\nde370\surfdrive\storage\CLUMondo simulations\LSCAM_InData\regioncambodia.asc'
props = arcpy.Describe(target)
arcpy.env.extent = props.extent
arcpy.env.outputCoordinateSystem = props.spatialReference
cellSizeMeter = props.meanCellHeight
arcpy.env.cellSize = cellSizeMeter # specification needed for cost distance algorithm
cellSize = cellSizeMeter/1000 # in kilometer
arcpy.env.snapRaster = target
targetObj = arcpy.sa.Raster(target)

#-------------------------------------------------------------------------------
# input parameters
# source points
source = r'C:\Users\nde370\surfdrive\storage\GeoData\Processing\Intermediate\accessibility\cambodia_location\cambodia_location_clip.shp'

# Setting the speeds (in km/h) you can reach on the different pixels
speed = {}
speed['water']          = 0.25
speed['primaryroad']    = 70
speed['secondaryroad']  = 30
speed['otherroad']      = 10
speed['smooth']         = 8
speed['rugged']         = 5
speed['veryrugged']     = 2

# setting the TRI classification scheme (cutoff values given below which TRI belonging to class)
THSmooth = 4
THRugged = 25

# ------------------------------------------------------------------------------
# Processing

# Make road cost raster
print 'generating road cost raster'
# --> rasterize
roadsRas = arcpy.PolylineToRaster_conversion(roads, "Cost", 'in_memory/roadsRas.tif', "MAXIMUM_LENGTH", "Cost", cellSizeMeter)
roadsRasObj = arcpy.sa.Raster(roadsRas)
# --> assign costs and fill no-data
roadsCost = arcpy.sa.Con(arcpy.sa.IsNull(roadsRas) & targetObj == 1, 0,\
            arcpy.sa.Con(roadsRasObj == 1,  float(1)/(speed['primaryroad']*1000),\
            arcpy.sa.Con(roadsRasObj == 2,  float(1)/(speed['secondaryroad']*1000), \
                                            float(1)/(speed['otherroad']*1000))))
# -->optional save of the cost surface
roadsCost.save(r'C:\Users\nde370\surfdrive\storage\GeoData\Processing\Scratch\roadsCost.tif')

# Make non-road cost raster
print 'generating off-road cost raster'
TRIObj = arcpy.sa.Raster(TRI)
offroadCost =   arcpy.sa.Con(TRIObj <= THSmooth,    float(1)/(speed['smooth']*1000),\
                arcpy.sa.Con(TRIObj <= THRugged,    float(1)/(speed['rugged']*1000),\
                                                    float(1)/(speed['veryrugged']*1000)))
# --> optional save of the cost surface
offroadCost.save(r'C:\Users\nde370\surfdrive\storage\GeoData\Processing\Scratch\offroadsCost.tif')

# Make Water cost raster
print 'generating water cost raster'
# --> rasterize
waterRas = arcpy.PolygonToRaster_conversion(water, "FID", r'C:\Users\nde370\surfdrive\storage\GeoData\Processing\Scratch\waterRas.tif', "MAXIMUM_AREA", "NONE", cellSizeMeter)
waterRasObj = arcpy.sa.Raster(waterRas)
# --> fill no-data
waterZero = arcpy.sa.Con(arcpy.sa.IsNull(waterRas) & targetObj == 1, 0, waterRas)
# --> assign cost (in seperate step because of some random error)
waterCost = arcpy.sa.Con(waterZero > 0, float(1)/(speed['water']*1000), 0)
# --> optional save of the cost surface
waterCost.save(r'C:\Users\nde370\surfdrive\storage\GeoData\Processing\Scratch\waterCost.tif')

# Create Cost surface
# --> logic: check if water, then check if road, else give off-road cost
print 'combining cost surfaces'
totalCost = arcpy.sa.Con(waterCost > 0, waterCost, \
            arcpy.sa.Con(roadsCost > 0, roadsCost, \
                                        offroadCost))
# --> optional save of the cost surface
totalCost.save(r'C:\Users\nde370\surfdrive\storage\GeoData\Processing\Scratch\totalCost.tif')

# Run cost distance
print 'running cost distance algorithm'
costDistance = arcpy.sa.CostDistance(source, totalCost, '', '')
costDistance.save(r'C:\Users\nde370\surfdrive\storage\GeoData\Processing\Scratch\costDistance.tif')

# clean memory
arcpy.Delete_management("in_memory")
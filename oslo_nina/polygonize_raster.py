#based on tutorial https://rasterio.readthedocs.io/en/latest/topics/features.html#extracting-shapes-of-raster-features
import rasterio, os, geojson, time
from rasterio import features


def img_in_dir(path):
    return [os.path.join(root, file) for root, _, files in os.walk(path) for file in files if file.endswith(".tif")]


def polygonize(img, classes, path, band=1, georeference=True, connectivity=4):
    if type(classes) is int:
        classes = [classes]
    with open(path, 'w') as file:
        with rasterio.open(img) as dataset:
            data_array = dataset.read(band)
            polygons = []
            for cls in classes:
                mask = data_array == cls
                if georeference:
                    shapes = features.shapes(data_array, mask=mask, transform=dataset.transform, connectivity=connectivity)
                else:
                    shapes = features.shapes(data_array, mask=mask, connectivity=connectivity)

                polygons = polygons + [geojson.Feature(geometry=shape[0], id=index, properties={"class": cls})
                            for index, shape in enumerate(shapes)]

        geofile = geojson.FeatureCollection(polygons)

        if georeference:
            crs = {"crs": { "type": "name", "properties": { "name": "epsg:{}".format(dataset.crs.to_epsg())}}}
            geofile.update(crs)
        geojson.dump(geofile, file)



if __name__ == '__main__':

    start = time.perf_counter()

    path = "C:\Michal\gisat\projects\\nina_oslo_tree\data\sentinel"
    output = "C:\Michal\gisat\projects\\nina_oslo_tree\data\sentinel\LULC_2015.geojson"
    years = ['2015', '2016', '2017', '2018', '2019']
    imgs = img_in_dir(path)
    for year,img in zip(years, imgs):
        polygonize(img, [1, 2, 3, 4], os.path.join(path, 'polygonized', f'LULC_{year}.geojson'))

    end = time.perf_counter()

    print(round(end-start, 2))
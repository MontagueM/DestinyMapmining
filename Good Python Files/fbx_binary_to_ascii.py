import fbx
import pyfbx_jo as pfb

direc = 'C:/d2_model_temp/ninjarips/prometheus_lens/Prometheus Lens.fbx'

model = pfb.FBox()
model.create_node()
model.import_file(direc, ascii_format=False)
model.export('C:/d2_model_temp/ninjarips/prometheus_lens/Prometheus Lens_ascii.fbx', ascii_format=True)
print('Done')
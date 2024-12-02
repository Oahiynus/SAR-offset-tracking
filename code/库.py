print("Hello, world!")
from snappy import ProductIO
file_path = r"E:/anaconda3/envs/snap_env/Lib/snappy/testdata/MER_FRS_L1B_SUBSET.dim"
p = ProductIO.readProduct(file_path)
list(p.getBandNames())
print(list(p.getBandNames()))
from snappy import ProductIO, GPF
from snappy import HashMap
import os

# 定义必要的文件路径
input_file_1 = "F:/data/MSR/data/original/S1A_IW_GRDH_1SDV_20180921T112511_20180921T112536_023796_029890_6709.zip"  # 第一时间段的GRD产品路径
input_file_2 = "F:/data/MSR/data/original/S1A_IW_GRDH_1SDV_20181003T112511_20181003T112536_023971_029E46_1361.zip"  # 第二时间段的GRD产品路径
output_dir = "F:/data/MSR/data/output_code"  # 输出文件夹路径
final_output_file = os.path.join(output_dir, "F:/data/MSR/data/output_code/glacier_velocity_map.dim")  # 最终结果路径

# 1. 读取输入数据
product1 = ProductIO.readProduct(input_file_1)
product2 = ProductIO.readProduct(input_file_2)

# 2. 应用轨道文件
def apply_orbit_file(product, output_name):
    params = HashMap()
    params.put("Apply-Orbit-File", True)
    result = GPF.createProduct("Apply-Orbit-File", params, product)
    output_path = os.path.join(output_dir, output_name)
    ProductIO.writeProduct(result, output_path, "BEAM-DIMAP")
    print(f"轨道文件应用完成: {output_path}")
    return result

product1_orbit = apply_orbit_file(product1, "orbit_corrected_1.dim")
product2_orbit = apply_orbit_file(product2, "orbit_corrected_2.dim")

# 3. 图像配准
def coregistration(master, slave, output_name):
    params = HashMap()
    params.put("DemName", "SRTM 3Sec")
    params.put("ResamplingType", "BISINC_5_POINT_INTERPOLATION")
    result = GPF.createProduct("Cross-Correlation", params, [master, slave])
    output_path = os.path.join(output_dir, output_name)
    ProductIO.writeProduct(result, output_path, "BEAM-DIMAP")
    print(f"图像配准完成: {output_path}")
    return result

coregistered_product = coregistration(product1_orbit, product2_orbit, "coregistered_product.dim")

# 4. 创建子集
def create_subset(product, region, output_name):
    params = HashMap()
    params.put("geoRegion", region)  # 根据你的兴趣区设置坐标
    result = GPF.createProduct("Subset", params, product)
    output_path = os.path.join(output_dir, output_name)
    ProductIO.writeProduct(result, output_path, "BEAM-DIMAP")
    print(f"子集创建完成: {output_path}")
    return result

geo_region = "POLYGON ((...))"  # 你的兴趣区域 (WKT格式)
subset_product = create_subset(coregistered_product, geo_region, "subset_product.dim")

# 5. 偏移追踪
def offset_tracking(product, output_name):
    params = HashMap()
    params.put("windowSize", "64x64")
    params.put("overlap", 0.5)
    result = GPF.createProduct("Offset-Tracking", params, product)
    output_path = os.path.join(output_dir, output_name)
    ProductIO.writeProduct(result, output_path, "BEAM-DIMAP")
    print(f"偏移追踪完成: {output_path}")
    return result

velocity_map = offset_tracking(subset_product, "velocity_map.dim")

# 6. 地形校正
def terrain_correction(product, output_name):
    params = HashMap()
    params.put("demName", "SRTM 1Sec HGT")
    params.put("pixelSpacingInMeter", 10.0)
    result = GPF.createProduct("Terrain-Correction", params, product)
    output_path = os.path.join(output_dir, output_name)
    ProductIO.writeProduct(result, output_path, "BEAM-DIMAP")
    print(f"地形校正完成: {output_path}")
    return result

terrain_corrected_velocity_map = terrain_correction(velocity_map, "terrain_corrected_velocity_map.dim")

# 7. 最终保存
ProductIO.writeProduct(terrain_corrected_velocity_map, final_output_file, "BEAM-DIMAP")
print(f"冰川流速图已生成并保存到: {final_output_file}")

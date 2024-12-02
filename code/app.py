import sys
import os

# 添加 SNAP 的 snappy 模块路径
snappy_path = "E:/anaconda3/envs/snap_env/Lib/snappy"
if snappy_path not in sys.path:
    sys.path.append(snappy_path)

# 检查路径是否正确
print("SNAPPY Path:", snappy_path)

# 导入必要的模块
from snappy import ProductIO, GPF
from snappy import HashMap
import os

# 设置输入和输出路径
# Sentinel-1 GRD 数据的输入路径
input_file_1 = "F:/data/MSR/data/original/S1A_IW_GRDH_1SDV_20181003T112511_20181003T112536_023971_029E46_1361.zip"
input_file_2 = "F:/data/MSR/data/original/S1A_IW_GRDH_1SDV_20181015T112511_20181015T112536_024146_02A3FF_5D3E.zip"

# 输出文件夹路径
output_dir = "F:/data/MSR/data/output_code_4"
# 最终滑坡形变图的输出路径
final_output_file = os.path.join(output_dir, "landslide_velocity_map.dim")

# 确保输出目录存在
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
print("输出目录:", output_dir)

# 加载输入数据
product1 = ProductIO.readProduct(input_file_1)  # 加载第一个时间点的 GRD 产品
product2 = ProductIO.readProduct(input_file_2)  # 加载第二个时间点的 GRD 产品

print("输入数据已加载:")
print("Product 1:", input_file_1)
print("Product 2:", input_file_2)

# **1. 应用轨道文件**
def apply_orbit_file(product, output_name):
    """
    对 Sentinel-1 GRD 产品应用精确轨道文件。
    轨道文件提高影像的几何定位精度。
    """
    params = HashMap()
    params.put("Apply-Orbit-File", True)  # 参数：启用轨道文件应用
    result = GPF.createProduct("Apply-Orbit-File", params, product)
    output_path = os.path.join(output_dir, output_name)  # 设置输出路径
    ProductIO.writeProduct(result, output_path, "BEAM-DIMAP")  # 保存结果
    print(f"轨道文件应用完成: {output_path}")
    return result

# 分别对两幅影像应用轨道文件
product1_orbit = apply_orbit_file(product1, "S1A_GRDH_20181003_Orb.dim")
product2_orbit = apply_orbit_file(product2, "S1A_GRDH_20181015_Orb.dim")

# **2. 图像配准**
def dem_assisted_coregistration_with_xcorr(master, slave, output_name):
    """
    使用 DEM-Assisted Coregistration with XCorr 进行影像配准。
    配准影像使两幅影像对齐，并结合地形校正功能。
    """
    params = HashMap()
    params.put("demName", "SRTM 3Sec")  # 使用 SRTM 3Sec DEM
    params.put("resamplingType", "BILINEAR_INTERPOLATION")  # 重采样方式：双线性插值
    params.put("maskOutAreaWithoutElevation", True)  # 遮蔽无 DEM 数据的区域
    params.put("xcorr", True)  # 启用交叉相关
    result = GPF.createProduct("DEM-Assisted-Coregistration", params, [slave, master])  # 执行配准
    output_path = os.path.join(output_dir, output_name)  # 输出路径
    ProductIO.writeProduct(result, output_path, "BEAM-DIMAP")  # 保存结果
    print(f"DEM辅助配准完成（使用 XCorr）: {output_path}")
    return result

# 执行影像配准
coregistered_product = dem_assisted_coregistration_with_xcorr(
    product1_orbit, product2_orbit, "S1A_GRDH_Orb_Stack.dim"
)

# **3. 创建子集**
def create_subset(product, region, output_name):
    """
    裁剪影像为指定的感兴趣区域（ROI）。
    """
    params = HashMap()
    params.put("geoRegion", region)  # 设置兴趣区域（WKT 格式）
    params.put("copyMetadata", True)  # 保留所有元数据
    try:
        result = GPF.createProduct("Subset", params, product)  # 执行子集裁剪
        if result is None:
            raise RuntimeError("子集裁剪未生成结果，请检查输入数据或裁剪区域。")
        output_path = os.path.join(output_dir, output_name)
        ProductIO.writeProduct(result, output_path, "BEAM-DIMAP")  # 保存结果
        print(f"子集裁剪完成，结果已保存到: {output_path}")
        return result
    except Exception as e:
        print("子集裁剪失败:", e)
        raise

# 定义裁剪区域（WKT 格式）
geo_region = "POLYGON ((98.696 31.112, 98.75 31.112, 98.75 31.06, 98.696 31.06, 98.696 31.112))"

# 创建子集
subset_product = create_subset(coregistered_product, geo_region, "S1A_GRDH_Orb_Stack_Subset.dim")

# **4. 偏移追踪**
def offset_tracking(product, output_name):
    """
    偏移追踪：估算两幅影像之间的地表运动。
    """
    params = HashMap()
    # 设置网格参数
    params.put("gridAzimuthSpacingInPixels", 14)  # 方位向网格间距
    params.put("gridRangeSpacingInPixels", 14)  # 距离向网格间距
    params.put("resamplingType", "BICUBIC_INTERPOLATION")  # 双三次插值
    # 设置注册参数
    params.put("registrationWindowWidth", 64)  # 注册窗口宽度
    params.put("registrationWindowHeight", 64)  # 注册窗口高度
    params.put("registrationOversampling", 16)  # 注册重采样倍数
    params.put("crossCorrelationThreshold", 0.1)  # 交叉相关阈值
    params.put("averageBoxSize", 5)  # 平均窗口大小
    params.put("maxVelocity", 50.0)  # 最大速度 (m/day)
    params.put("radiusForHoleFilling", 10)  # 填洞半径
    params.put("spatialAverage", True)  # 空间平均
    params.put("fillHoles", True)  # 填充洞
    try:
        print("开始偏移追踪...")
        result = GPF.createProduct("Offset-Tracking", params, product)
        if result is None:
            raise RuntimeError("偏移追踪未生成结果，请检查输入数据或参数设置。")
        output_path = os.path.join(output_dir, output_name)
        ProductIO.writeProduct(result, output_path, "BEAM-DIMAP")  # 保存结果
        print(f"偏移追踪完成，结果已保存到: {output_path}")
        return result
    except Exception as e:
        print("偏移追踪失败:", e)
        raise

# 执行偏移追踪
velocity_map = offset_tracking(subset_product, "S1A_GRDH_Orb_Stack_Subset_velocity.dim")

# **5. 地形校正**
def terrain_correction(product, output_name):
    """
    地形校正：对生成的速度场进行正射校正。
    """
    params = HashMap()
    params.put("demName", "SRTM 3Sec")  # 使用 SRTM 3Sec DEM
    params.put("pixelSpacingInMeter", 10.0)  # 设置分辨率为 10 米
    result = GPF.createProduct("Terrain-Correction", params, product)  # 执行地形校正
    output_path = os.path.join(output_dir, output_name)
    ProductIO.writeProduct(result, output_path, "BEAM-DIMAP")  # 保存结果
    print(f"地形校正完成: {output_path}")
    return result

# 执行地形校正
terrain_corrected_velocity_map = terrain_correction(velocity_map, "terrain_corrected_velocity_map.dim")

# **6. 保存最终结果**
ProductIO.writeProduct(terrain_corrected_velocity_map, final_output_file, "BEAM-DIMAP")
print(f"滑坡形变图已生成并保存到: {final_output_file}")

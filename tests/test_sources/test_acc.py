import time
import json
import random
import os
import sys
from typing import List, Dict, Optional, Tuple, Any  # 确保全量导入

# ===================== 全局性能跟踪器（单例模式） =====================
class PerformanceTracker:
    """性能跟踪类：记录函数执行时间，生成速度对比报告"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 修复：显式初始化字典（避免类型注解报错）
            cls._instance.perf_records = {}
        return cls._instance

    def track(self, func):
        """装饰器：自动记录函数执行时间"""
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            if func.__name__ not in self.perf_records:
                self.perf_records[func.__name__] = []
            self.perf_records[func.__name__].append(elapsed)
            return result
        return wrapper

    def get_avg_time(self, func_name: str) -> float:
        """快速函数：获取函数平均耗时"""
        if func_name not in self.perf_records or not self.perf_records[func_name]:
            return 0.0
        return sum(self.perf_records[func_name]) / len(self.perf_records[func_name])

    def generate_perf_report(self) -> str:
        """中速函数：生成性能对比报告"""
        report = "\n======= 函数速度测试报告 =======\n"
        # 按最新耗时排序
        sorted_records = sorted(
            self.perf_records.items(),
            key=lambda x: x[1][-1] if x[1] else 0,
            reverse=True
        )
        for func_name, times in sorted_records:
            avg = self.get_avg_time(func_name)
            latest = times[-1] if times else 0.0
            if latest > 1:
                speed_level = "【极慢】"
            elif latest > 0.1:
                speed_level = "【慢速】"
            elif latest > 0.01:
                speed_level = "【中速】"
            else:
                speed_level = "【快速】"
            report += (
                f"{speed_level} {func_name:<25} "
                f"最新耗时: {latest:.6f}s  "
                f"平均耗时: {avg:.6f}s  "
                f"执行次数: {len(times)}\n"
            )
        report += "=================================\n"
        return report

    def save_report(self, file_path: str = "perf_report.txt") -> bool:
        """中速函数：保存性能报告到文件"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.generate_perf_report())
            print(f"性能报告已保存至: {file_path}")
            return True
        except Exception as e:
            print(f"保存报告失败: {str(e)}")
            return False

# 初始化全局跟踪器 + 导出装饰器（核心修复：避免装饰器未定义）
global_tracker = PerformanceTracker()
track = global_tracker.track

# ===================== 基础数据处理器（父类） =====================
class BaseDataHandler:
    """基础数据处理器：通用数据验证、错误处理"""
    def __init__(self):
        self.tracker = global_tracker
        self.error_count = 0  # type: int
        self.valid_data_count = 0  # type: int
        self.supported_formats = ["json", "txt"]  # type: List[str]

    @track
    def validate_str(self, value: Any) -> bool:
        """快速函数（O(1)）：验证字符串有效性"""
        if isinstance(value, str) and len(value.strip()) > 0:
            self.valid_data_count += 1
            return True
        self.error_count += 1
        return False

    @track
    def validate_int(self, value: Any, min_val: int = 0) -> bool:
        """快速函数（O(1)）：验证整数有效性"""
        if isinstance(value, int) and value >= min_val:
            self.valid_data_count += 1
            return True
        self.error_count += 1
        return False

    @track
    def clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """中速函数（O(n)）：清理数据空值"""
        cleaned = {}
        for k, v in data.items():
            if v is not None and v != "":
                cleaned[k] = v
        time.sleep(0.001 * len(cleaned))  # 模拟延迟
        return cleaned

    @track
    def get_error_stats(self) -> Tuple[int, int]:
        """快速函数：获取数据校验统计"""
        return self.error_count, self.valid_data_count

    @track
    def reset_stats(self) -> None:
        """快速函数：重置统计数据"""
        self.error_count = 0
        self.valid_data_count = 0

# ===================== 订单数据处理器（子类） =====================
class OrderDataHandler(BaseDataHandler):
    """订单数据处理器：订单CRUD、导入导出"""
    def __init__(self):
        super().__init__()
        self.orders = []  # type: List[Dict[str, Any]]
        self.order_id_counter = 10000  # type: int

    @track
    def generate_test_orders(self, count: int) -> List[Dict[str, Any]]:
        """中速函数（O(n)）：生成测试订单数据"""
        orders = []
        products = ["手机", "电脑", "耳机", "键盘", "鼠标", "充电器", "数据线"]
        status_list = ["待付款", "已付款", "已发货", "已完成", "已取消"]
        
        for i in range(count):
            order_id = f"ORD{self.order_id_counter + i}"
            amount = random.randint(10, 5000)
            # 构造订单数据
            order = {
                "order_id": order_id,
                "user_id": f"USR{random.randint(1000, 9999)}",
                "product": random.choice(products),
                "amount": amount,
                "quantity": random.randint(1, 10),
                "status": random.choice(status_list),
                "create_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "pay_time": time.strftime("%Y-%m-%d %H:%M:%S") if random.random() > 0.3 else None
            }
            if i % 1000 == 0:
                time.sleep(0.001)  # 模拟批量延迟
            orders.append(order)
        
        self.orders = orders
        self.order_id_counter += count
        print(f"生成{count}条测试订单数据完成")
        return orders

    @track
    def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """快速函数（O(n)）：按ID查询订单"""
        if not self.validate_str(order_id):
            return None
        for order in self.orders:
            if order.get("order_id") == order_id:
                return order
        return None

    @track
    def filter_orders_by_status(self, status: str) -> List[Dict[str, Any]]:
        """中速函数（O(n)）：按状态筛选订单"""
        if not self.validate_str(status):
            return []
        filtered = []
        for order in self.orders:
            if order.get("status") == status:
                filtered.append(order)
                time.sleep(0.0001)  # 模拟筛选延迟
        return filtered

    @track
    def export_orders_to_file(self, file_path: str, format_type: str = "json") -> bool:
        """慢速函数（O(n) + IO）：导出订单到文件"""
        if format_type not in self.supported_formats:
            self.error_count += 1
            print(f"不支持的格式：{format_type}")
            return False
        
        try:
            time.sleep(0.002 * len(self.orders))  # 模拟IO延迟
            with open(file_path, "w", encoding="utf-8") as f:
                if format_type == "json":
                    json.dump(self.orders, f, ensure_ascii=False, indent=2)
                else:
                    f.write("订单ID,用户ID,商品,金额,数量,状态,创建时间\n")
                    for order in self.orders:
                        f.write(
                            f"{order['order_id']},{order['user_id']},"
                            f"{order['product']},{order['amount']},{order['quantity']},"
                            f"{order['status']},{order['create_time']}\n"
                        )
            print(f"订单数据已导出至: {file_path}")
            return True
        except Exception as e:
            self.error_count += 1
            print(f"导出失败: {str(e)}")
            return False

    @track
    def import_orders_from_file(self, file_path: str) -> bool:
        """中速函数（O(n) + IO）：从文件导入订单"""
        if not os.path.exists(file_path):
            self.error_count += 1
            print(f"文件不存在：{file_path}")
            return False
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if file_path.endswith(".json"):
                    self.orders = json.load(f)
                else:
                    self.orders = []
                    lines = f.readlines()[1:]  # 跳过表头
                    for line in lines:
                        parts = line.strip().split(",")
                        if len(parts) >= 6:
                            order = {
                                "order_id": parts[0],
                                "user_id": parts[1],
                                "product": parts[2],
                                "amount": int(parts[3]),
                                "quantity": int(parts[4]),
                                "status": parts[5],
                                "create_time": parts[6] if len(parts) > 6 else ""
                            }
                            self.orders.append(order)
                            time.sleep(0.0001)  # 模拟导入延迟
            print(f"从{file_path}导入{len(self.orders)}条订单数据")
            return True
        except Exception as e:
            self.error_count += 1
            print(f"导入失败: {str(e)}")
            return False

# ===================== 订单分析器（子类） =====================
class OrderAnalyzer(OrderDataHandler):
    """订单分析器：统计、排序、报表生成"""
    def __init__(self):
        super().__init__()
        self.analysis_results = {}  # type: Dict[str, Any]

    @track
    def calculate_total_sales(self) -> float:
        """中速函数（O(n)）：计算总销售额"""
        total = 0.0
        for order in self.orders:
            if order.get("status") in ["已付款", "已发货", "已完成"]:
                total += order.get("amount", 0) * order.get("quantity", 0)
                time.sleep(0.0001)  # 模拟计算延迟
        self.analysis_results["total_sales"] = total
        return total

    @track
    def get_top_products(self, top_n: int = 5) -> List[Tuple[str, int]]:
        """中速函数（O(n)）：统计销量TOP商品"""
        product_stats = {}  # type: Dict[str, int]
        for order in self.orders:
            if order.get("status") != "已取消":
                product = order.get("product")
                product_stats[product] = product_stats.get(product, 0) + order.get("quantity", 0)
        
        # 排序取TOP N
        sorted_products = sorted(
            product_stats.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        self.analysis_results["top_products"] = sorted_products
        return sorted_products

    @track
    def bubble_sort_orders_by_amount(self) -> List[Dict[str, Any]]:
        """极慢速函数（O(n²)）：冒泡排序订单（按金额）"""
        orders_copy = self.orders.copy()
        n = len(orders_copy)
        
        # 冒泡排序（低效算法，突出速度差异）
        for i in range(n):
            for j in range(0, n - i - 1):
                if orders_copy[j].get("amount", 0) < orders_copy[j+1].get("amount", 0):
                    orders_copy[j], orders_copy[j+1] = orders_copy[j+1], orders_copy[j]
                time.sleep(0.00005)  # 放大排序延迟
        
        self.analysis_results["sorted_orders_bubble"] = orders_copy[:10]
        return orders_copy

    @track
    def quick_sort_orders_by_amount(self) -> List[Dict[str, Any]]:
        """快速函数（O(n log n)）：快速排序订单（按金额）"""
        sorted_orders = sorted(
            self.orders,
            key=lambda x: x.get("amount", 0),
            reverse=True
        )
        self.analysis_results["sorted_orders_quick"] = sorted_orders[:10]
        return sorted_orders

    @track
    def generate_sales_report(self, file_path: str = "sales_report.txt") -> bool:
        """慢速函数（O(n) + IO）：生成销售分析报告"""
        try:
            total_sales = self.calculate_total_sales()
            top_products = self.get_top_products()
            
            # 统计订单状态分布
            status_stats = {}  # type: Dict[str, int]
            for status in ["待付款", "已付款", "已发货", "已完成", "已取消"]:
                status_stats[status] = len(self.filter_orders_by_status(status))
            
            # 生成报告内容
            report = f"""================ 电商订单销售报告 ================
生成时间：{time.strftime("%Y-%m-%d %H:%M:%S")}
总订单数：{len(self.orders)}
总销售额：¥{total_sales:.2f}
订单状态分布：
"""
            for status, count in status_stats.items():
                ratio = count / len(self.orders) * 100 if self.orders else 0
                report += f"  {status}: {count} 单（占比：{ratio:.1f}%）\n"
            
            report += "销量TOP5商品：\n"
            for idx, (product, qty) in enumerate(top_products, 1):
                report += f"  {idx}. {product}: {qty} 件\n"
            report += "==============================================="
            
            time.sleep(0.1)  # 模拟报告生成延迟
            # 写入文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report)
            
            print(f"销售报告已生成至: {file_path}")
            return True
        except Exception as e:
            self.error_count += 1
            print(f"生成报告失败: {str(e)}")
            return False

# ===================== 主程序（可直接执行） =====================
def main():
    """主函数：完整业务流程 + 速度测试"""
    # 环境检查
    if sys.version_info < (3, 6):
        print("错误：本程序需要Python 3.6及以上版本！")
        sys.exit(1)
    
    print("======= 电商订单管理系统（速度测试版） =======")
    # 初始化分析器
    analyzer = OrderAnalyzer()
    
    # 1. 生成测试订单数据
    print("\n=== 步骤1：生成测试订单数据 ===")
    analyzer.generate_test_orders(count=1000)  # 可调整数量放大速度差异
    
    # 2. 基础订单操作
    print("\n=== 步骤2：基础订单操作（快速/中速） ===")
    # 快速查询
    order = analyzer.get_order_by_id("ORD10005")
    print(f"查询订单ORD10005：{order.get('product') if order else '不存在'}")
    # 中速筛选
    completed_orders = analyzer.filter_orders_by_status("已完成")
    print(f"已完成订单数：{len(completed_orders)}")
    # 中速导出
    analyzer.export_orders_to_file("test_orders.json")
    
    # 3. 订单分析（速度差异核心测试）
    print("\n=== 步骤3：订单分析（中速/慢速/极慢速） ===")
    # 中速：计算总销售额
    total_sales = analyzer.calculate_total_sales()
    print(f"总销售额：¥{total_sales:.2f}")
    # 中速：TOP5商品
    top_products = analyzer.get_top_products()
    print(f"销量TOP5：{top_products}")
    # 快速：快速排序
    print("开始快速排序订单（O(n log n)）...")
    analyzer.quick_sort_orders_by_amount()
    # 极慢速：冒泡排序
    print("开始冒泡排序订单（O(n²)，请稍候）...")
    analyzer.bubble_sort_orders_by_amount()
    # 慢速：生成报告
    analyzer.generate_sales_report()
    
    # 4. 生成性能报告（核心测试结果）
    print("\n=== 步骤4：生成速度测试报告 ===")
    print(global_tracker.generate_perf_report())
    global_tracker.save_report()
    
    # 5. 清理测试文件
    print("\n=== 步骤5：清理测试文件 ===")
    test_files = ["test_orders.json", "sales_report.txt", "perf_report.txt"]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"已删除：{file}")

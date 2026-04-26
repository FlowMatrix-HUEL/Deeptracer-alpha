# test_with_memory.py - 包含大量内存占用，用于测试分析效果
import time

# 1. 创建大列表（占用明显内存）
large_list = [i for i in range(100000)]  # 约几百KB内存
print(f"大列表长度：{len(large_list)}")

# 2. 创建大字典
large_dict = {f"key_{i}": [j for j in range(100)] for i in range(1000)}
print(f"大字典键数量：{len(large_dict)}")

# 3. 循环占用内存（延长执行时间，确保快照能捕获）
temp_list = []
for i in range(5000):
    temp_list.append(f"test_string_{i}" * 10)
    time.sleep(0.001)  # 轻微延时，确保内存被统计

# 4. 计算总和（触发内存使用）
total = sum(large_list)
print(f"大列表总和：{total}")

# 5. 手动保留变量（避免被GC回收）
del temp_list[:500]  # 部分删除，保留剩余数据


from pyvis.network import Network
import networkx
import ast
import os 
from deeptracer import print_color
import uuid
from deeptracer.astAnalyer.env_utils import TYPES


class AstAnalyer:
    """
    AST语法树分析模块 实现对代码分析后生成可视化结构
    
    Args:
        pythonScript(stra检测文件路径)

    Attributes:
        None
    
    Methods:
        None
    """
    def __init__(self,
                 pythonScript:str = None,
                 open:bool=True,
                 core_node_types:tuple=TYPES
                )->None:
        """
        初始化函数
        
        Args:
            pythonScript(str):python源文件路径
            save_path(str):检验结果存储路径
            open(bool):是不是开启ast过滤
            core_node_types(tuple):保留类别
        Returns:
            None
        """
        self.pythonScript = pythonScript
        #如果存在之前缓存删除缓存代码
        self.open = open
        if self.open:
            self.core_node_types = core_node_types
        #如果选者开启过滤 只保留以上的语法节点
        self.graph = networkx.DiGraph()
        #建立网络对象
        root = self._get_ast()
        #获得Moudel对象是代码起始点
        self._traverse_ast(root)
        #执行网络填充
    def _get_target_code(self,
                         pythonScript:str,
                         )->str:
        
        """
        获取指定路径下的python源代码

        Args:
            pythonScript(str):python源文件路径
        Returns:
            code(str):python源代码
        
        """
        if not os.path.exists(pythonScript):
            raise FileExistsError(f"{pythonScript}函数不存在!")
        try:
            with open(pythonScript,"r",encoding="utf-8") as fp:
                code = fp.read()
        except Exception as e:
            raise FileNotFoundError(f"{pythonScript}无法正常打开")
        
        return code
    
    def _get_ast(self)->ast.Module:
        """
        获得ast语法树

        Args:
            None
        Returns:
            tree(ast.Module):目标代码下的ast语法树
        """
        code = self._get_target_code(self.pythonScript)
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"代码语法错误: {e}")
        return tree
    
    def _traverse_ast(self, 
                      node: ast.AST|list|str, 
                      parent_id: str = None
                      )->None:
        """
        递归遍历AST 构建图节点和边
        
        Args:
            node(ast.ASt):当前节点
            parent_id(str):父节点id

        Returns:
            None
        """
        if not node:
            return
        if not isinstance(node,(list,ast.AST)):
            return
        if isinstance(node,ast.AST) and self.open:
            if type(node).__name__ not in self.core_node_types:
                return
        
        node_info = self._get_node_info(node)
        node_id = node_info["id"]
        #建立唯一标识索引表

        self.graph.add_node(
            node_id,
            label=node_info['label'],
            title=f"type: {node_info['type']}\nattribute: {node_info['attrs']}",  # 鼠标悬浮提示
            color=self._get_node_color(node_info['type']),  # 按类型着色
            size=15  # 节点大小
        )
        if parent_id:
            self.graph.add_edge(parent_id, node_id, label="parent")
        
        for _,field_values in ast.iter_fields(node):
            #遍历每一个子节点
            if isinstance(field_values, list):
                for _, child in enumerate(field_values):
                    self._traverse_ast(child, node_id)
            else:
                self._traverse_ast(field_values, node_id)
                #如果节点不可迭代直接调度
    def _get_node_color(self,
                        node_type: str
                        ) -> str:
        """
        按节点类型分配颜色，增强可读性

        Args:
            node_type(str):类别字符串
        Returns:
            color(str):颜色信息
        """
        color_map = {    
            'Module': '#1f77b4',
            'Name': '#ff7f0e',
            'Constant': '#2ca02c',    
            'Assign': '#d62728',
            'If': '#9467bd',
            'For': '#8c564b',
            'FunctionDef': '#e377c2',
            'BinOp': '#7f7f7f',
            'Call': '#bcbd22',
            'Compare': '#17becf',
            'ClassDef': '#4CAF50',      
            'FunctionDef': '#e377c2',   
            'AsyncFunctionDef': '#FF9800'
        }
        return color_map.get(node_type,
                             '#000000')  #如果找不到默认为黑色
    def _get_node_info(self,
                       node:ast.AST
                       )->dict:
        """
        获得节点信息
        
        Args:
            node(ast.AST):获得信息节点

        Returns:
            node_info(dict):节点信息

        """
        node_type = type(node).__name__
        
        # 提取节点的核心属性
        attrs = {}
        if hasattr(node, 'id'):  # 变量名/函数名
            attrs['id'] = node.id
        if hasattr(node, 'n'):  # 数字常量
            attrs['value'] = node.n
        if hasattr(node, 's'):  # 字符串常量
            attrs['value'] = node.s
        if hasattr(node, 'op'):  # 运算符
            attrs['operator'] = type(node.op).__name__
        if hasattr(node, 'func') and hasattr(node.func, 'id'):  # 函数调用
            attrs['function'] = node.func.id
        # 拼接节点标签（类型 + 核心属性）
        label = f"{node_type}\n{attrs}" if attrs else node_type
        return {
            'id': str(uuid.uuid4()),  # 唯一ID
            'type': node_type,
            'attrs': attrs,
            'label': label
        }
    def visualize(self,
                  )->None:
        """
        生成交互式可视化网页
        
        Args:
            None
        Returns:
            None
        """
        # 初始化pyvis网络（设置尺寸、是否可交互）
        net = Network(
            height='800px',
            width='100%',
            directed=True,  # 有向图
            bgcolor="#f9f8fa",
            font_color='#000000'
        )
        
        # 将networkx的节点和边导入pyvis
        net.from_nx(self.graph)
        
        # 优化布局
        net.set_options("""
        var options = {
          "physics": {
            "forceAtlas2Based": {
              "gravitationalConstant": -50,
              "centralGravity": 0.01,
              "springLength": 100,
              "springConstant": 0.08
            },
            "maxVelocity": 50,
            "solver": "forceAtlas2Based",
            "timestep": 0.35,
            "stabilization": {
              "iterations": 150
            }
          }
        }
        """)
        
        # 生成HTML文件
        core_html = net.generate_html()
        print_color(f"AST可视化已生成",
                    fore_color="green")
        return core_html
class CodeStructureAnalyzer(AstAnalyer):
        """
        代码的类与函数的结构可视化 
        
        Args:
             pythonScript(str):python源文件路径
        Attributes:
            None
    
        Methods:
            None
        """
        def __init__(self,
                    pythonScript:str = None,
                    )->None:
            """
            初始化函数

            Args:
                pythonScript(str):python源文件路径
                save_path(str):检验结果存储路径

            Returns:
                None            
            """
            open = True
            core_node = (
                (
                'Module',      
                'ClassDef',    
                'FunctionDef',  
                'AsyncFunctionDef',  
            )
            )
            super().__init__(pythonScript=pythonScript,
                             open=open,
                             core_node_types=core_node
                             )
            

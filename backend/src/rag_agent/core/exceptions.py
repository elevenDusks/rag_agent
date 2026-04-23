"""异常模块

该模块定义了应用中使用的各种异常类，用于处理不同类型的错误情况。
"""
class RAGAgentException(Exception):
    """RAG Agent 基础异常类
    
    所有 RAG Agent 相关的异常都继承自此类。
    """
    pass

class DocumentIngestionError(RAGAgentException):
    """文档导入错误
    
    当文档导入失败时抛出的异常。
    """
    pass

class SearchError(RAGAgentException):
    """搜索错误
    
    当搜索操作失败时抛出的异常。
    """
    pass

class ChatError(RAGAgentException):
    """聊天生成错误
    
    当聊天回答生成失败时抛出的异常。
    """
    pass

class ConfigurationError(RAGAgentException):
    """配置错误
    
    当配置无效时抛出的异常。
    """
    pass

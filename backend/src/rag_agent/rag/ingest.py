from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader, JSONLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path

from ..models.model_registry import embedding_model
from ..core.config import settings
from ..core.logger import logger

# 项目根目录地址
BASE_URL = Path(__file__).parents[4]
# print(f"BASE_URL:{BASE_URL}")

# 法律文档切割文档参数
chunk_size_law = 1000
chunk_overlap_law = 150
separators_law=["\n\n", "\n", "。", "！", "？", " "]

# 京东帮助文档切割文档参数
chunk_size_jd = 800
chunk_overlap_jd = 100
separators_jd=separators = [
    "\n## ",          # 一级章节分隔符
    "\n### ",          # 二级子章节分隔符
    "\n#### ",         # 三级子章节分隔符
    "\n1. ",           # 有序列表项分隔符
    "\n- ",            # 无序列表项分隔符
    "\n| ",            # 表格行分隔符
    "\n"               # 换行符（作为最后的兜底分隔符）
]


# 导入地址 和 名称
CHROMA_PATH = settings.CHROMA_DB_PATH # 向量数据库存储路径
DOCUMENT_PATH_JD = BASE_URL/settings.DOCUMENT_PATH_JD # 京东帮助文档存储路径
DOCUMENT_PATH_LAW = BASE_URL/settings.DOCUMENT_PATH_LAW # 法律文档存储路径
# print(f"DOCUMENT_PATH_JD:{DOCUMENT_PATH_JD}")

# Chroma存储地址
CHROMA_DB_PATH = str(BASE_URL/settings.CHROMA_DB_PATH)
# print(f"CHROMA_DB_PATH:{CHROMA_DB_PATH}")
# print(type(CHROMA_DB_PATH))

# Chroma集合名称
CHROMA_DB_JD = settings.CHROMA_NAME_JD # 京东帮助文档集合名称
CHROMA_DB_LAWS = settings.CHROMA_NAME_LAWS # 法律集合名称



def ingest():
    # 文档加载
    logger.info(f"正在加载文档: {DOCUMENT_PATH_JD}")
    jd_help_path_doc = UnstructuredMarkdownLoader(DOCUMENT_PATH_JD).load()
    logger.info(f"JD文档加载完成，共 {len(jd_help_path_doc)} 个文档")
    
    logger.info(f"正在加载文档: {DOCUMENT_PATH_LAW}")
    law_doc = TextLoader(DOCUMENT_PATH_LAW, encoding="utf-8").load()
    logger.info(f"法律文档加载完成，共 {len(law_doc)} 个文档")

    # 法律条文的文档拆分
    law_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size_law,  # 每块最大500字
        chunk_overlap=chunk_overlap_law,  # 重叠50字，防止语义断裂
        separators=separators_law,  # 中文友好分隔符
        length_function=len
    )

    law_chunks = law_splitter.split_documents(law_doc)
    logger.info(f"法律文档切分完成，共 {len(law_chunks)} 个块")

    # 京东帮助文档的文档拆分
    jd_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size_jd,  # 足够容纳最长的二级标题内容（最长约400字）
        chunk_overlap=chunk_overlap_jd,  # 二级标题之间主题独立，无需重叠
        # 优先按标题拆分
        separators=separators_jd,
        length_function=len
    )

    jd_help_chunks = jd_splitter.split_documents(jd_help_path_doc)
    logger.info(f"JD文档切分完成，共 {len(jd_help_chunks)} 个块")


    # print("embedding_model:", embedding_model)

    # 获取向量数据库
    logger.info(f"\n正在创建向量数据库集合: {CHROMA_DB_JD}")
    jd_db = Chroma(
        collection_name=CHROMA_DB_JD,
        persist_directory=CHROMA_DB_PATH,
        embedding_function=embedding_model.model
    )

    logger.info(f"正在创建向量数据库集合: {CHROMA_DB_LAWS}")
    laws_db = Chroma(
        collection_name=CHROMA_DB_LAWS,
        embedding_function=embedding_model.model,
        persist_directory=CHROMA_DB_PATH
    )

    # print(jd_db)
    # print(ex_db)
    # print(laws_db)

    # 将数据存入向量数据库
    logger.info(f"\n正在向 {CHROMA_DB_JD} 添加文档...")
    jd_db.add_documents(jd_help_chunks)
    logger.info(f"成功添加 {len(jd_help_chunks)} 个文档到 {CHROMA_DB_JD}")
    
    logger.info(f"正在向 {CHROMA_DB_LAWS} 添加文档...")
    laws_db.add_documents(law_chunks)
    logger.info(f"成功添加 {len(law_chunks)} 个文档到 {CHROMA_DB_LAWS}")
    
    logger.info("\n✅ 数据导入完成！")

def test():
    embeddings = embedding_model.model
    db = Chroma(
        persist_directory=CHROMA_DB_PATH,
        embedding_function=embeddings,
        collection_name = "jd_help"  # 你的集合名
    )

    # 4. 相似度检索（测试问题，随便改）
    query = "新用户需要注册账号，已注册用户"
    docs = db.similarity_search(query, k=2)  # k=返回2条最相似的结果

    # 5. 打印结果（能出内容=成功）
    print("检索成功！匹配到的内容：")
    print(len(docs))
    for i, doc in enumerate(docs):
        print(f"\n===== 结果{i + 1} =====")
        print(doc.page_content)

if __name__ == "__main__":

    ingest()

    # test()

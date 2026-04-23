# # 允许所有IP访问（Docker容器间通信必需，配合密码保护）
# bind 0.0.0.0
#
# # 统一端口，本地和生产都用6379
# port 6379
#
# # 开发密码，部署时在.env里覆盖即可
# requirepass dev_redis_123456
#
# # 开启AOF持久化，防止RAG缓存和会话数据丢失
# appendonly yes
# appendfsync everysec
#
# # 禁用危险命令（生产必备，开发也先加上）
# rename-command FLUSHDB ""
# rename-command FLUSHALL ""
# rename-command CONFIG ""
#
# # 内存限制，根据你的服务器调整
# maxmemory 1gb
# maxmemory-policy allkeys-lru
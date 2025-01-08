import redis

from environs import Env

env = Env()
env.read_env()
redis_host = env.str('REDIS_HOST')
redis_port = env.str('REDIS_PORT')
redis_password = env.str('REDIS_PASSWORD')


r = redis.StrictRedis(
    host=redis_host,
    port=redis_port,
    decode_responses=True,
    charset="utf-8",
    password=redis_password,
)

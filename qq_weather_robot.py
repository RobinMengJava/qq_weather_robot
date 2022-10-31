import asyncio
import json
import os.path
import threading
from typing import Dict, List
import aiohttp
import qqbot
import time

from qqbot.core.util.yaml_util import YamlUtil
from qqbot.model.message import MessageEmbed, MessageEmbedField, MessageEmbedThumbnail, CreateDirectMessageRequest, \
    MessageArk, MessageArkKv, MessageArkObj, MessageArkObjKv

robot_config = YamlUtil.read(os.path.join(os.path.dirname(__file__), "config.yaml"))

public_channel_id = ""

async def _message_event_handler(event, message: qqbot.Message):
    msg_api = qqbot.AsyncMessageAPI(t_token, False)
    content = message.content
    if "/天气" in content:
        split = content.split("/天气 ")
        weather = await get_city_weather(split[1])
        await send_weather_ark_message(weather, message.channel_id, message.id)
    elif "/私信天气" in content:
        split = content.split("/私信天气 ")
        weather = await get_city_weather(split[1])
        await send_weather_private_message(weather, message.guild_id, message.author.id)

async def get_city_weather(city_name: str) -> Dict:
    weather_api_url = "http://api.k780.com/?app=weather.today&cityNm=" + city_name + "&appkey=67705&sign=80eebbcf357b4ed958ed254826a0e6ff&format=json"
    async with aiohttp.ClientSession() as session:
        async with session.get(
                url=weather_api_url,
                timeout=5,
        ) as resp:
            content = await resp.text()
            content_json_obj = json.loads(content)
            return content_json_obj

async def _create_ark_obj_list(weather_dict) -> List[MessageArkObj]:
    obj_list = [MessageArkObj(obj_kv=[MessageArkObjKv(key="desc", value=weather_dict['result']['citynm'] + " " + weather_dict['result']['weather'] +  " " + weather_dict['result']['days'] + " " + weather_dict['result']['week'])]),
                MessageArkObj(obj_kv=[MessageArkObjKv(key="desc", value="当日温度区间：" + weather_dict['result']['temperature'])]),
                MessageArkObj(obj_kv=[MessageArkObjKv(key="desc", value="当前温度：" + weather_dict['result']['temperature_curr'])]),
                MessageArkObj(obj_kv=[MessageArkObjKv(key="desc", value="当前湿度：" + weather_dict['result']['humidity'])])]
    return obj_list

async def send_weather_ark_message(weather_dict, channel_id, message_id):

    ark = MessageArk()
    ark.template_id = 23
    ark.kv = [MessageArkKv(key="#DESC#", value="描述"),
              MessageArkKv(key="#PROMPT#", value="提示消息"),
              MessageArkKv(key="#LIST#", obj=await _create_ark_obj_list(weather_dict))]
    send = qqbot.MessageSendRequest(content="", ark=ark, msg_id=message_id)
    msg_api = qqbot.AsyncMessageAPI(t_token, False)
    await msg_api.post_message(channel_id, send)

async def send_weather_private_message(weather_dict, guild_id, user_id):

    embed = MessageEmbed()
    embed.title = weather_dict['result']['citynm'] + " " + weather_dict['result']['weather']
    embed.prompt = "天气消息推送"
    thumbnail = MessageEmbedThumbnail()
    thumbnail.url = weather_dict['result']['weather_icon']
    embed.thumbnail = thumbnail
    embed.fields = [MessageEmbedField(name="当日温度区间：" + weather_dict['result']['temperature']),
                    MessageEmbedField(name="当前温度：" + weather_dict['result']['temperature_curr']),
                    MessageEmbedField(name="最高温度：" + weather_dict['result']['temp_high']),
                    MessageEmbedField(name="最低温度：" + weather_dict['result']['temp_low']),
                    MessageEmbedField(name="当前湿度：" + weather_dict['result']['humidity'])]

    send = qqbot.MessageSendRequest(embed=embed, content="")
    dms_api = qqbot.AsyncDmsAPI(t_token, False)
    direct_message_guild = await dms_api.create_direct_message(CreateDirectMessageRequest(guild_id, user_id))
    await dms_api.post_direct_message(direct_message_guild.guild_id, send)
    
if __name__ == "__main__":
    t_token = qqbot.Token(robot_config["token"]["appid"], robot_config["token"]["token"])
    qqbot_handler = qqbot.Handler(
        qqbot.HandlerType.AT_MESSAGE_EVENT_HANDLER, _message_event_handler
    )
    qqbot.async_listen_events(t_token, False, qqbot_handler)
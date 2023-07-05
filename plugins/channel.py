import pymongo
from pyrogram import Client, filters
from info import DATABASE_URI , DATABASE_NAME , COLLECTION_NAME , ADMINS , CHANNELS , CUSTOM_FILE_CAPTION
from database.ia_filterdb import save_file
import asyncio
import random

media_filter = filters.document | filters.video | filters.audio

myclient = pymongo.MongoClient(DATABASE_URI)
db=myclient[DATABASE_NAME]
col=db[COLLECTION_NAME]

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    """Media Handler"""
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media is not None:
            break
    else:
        return

    media.file_type = file_type
    media.caption = message.caption
    await save_file(media)

@Client.on_message(filters.command("savefile") & filters.user(ADMINS))
async def start(client, message):
    try:
        for file_type in ("document", "video", "audio"):
            media = getattr(message.reply_to_message , file_type, None)
            if media is not None:
                break
        else:
            return

        media.file_type = file_type
        media.caption = message.reply_to_message.caption
        await save_file(media)
        await message.reply_text("**Saved In DB**")
    except Exception as e:
        await message.reply_text(f"**Error :- {str(e)}**")

@Client.on_message(filters.command("sendall") & filters.user(ADMINS))
async def x(app , msg):
    args=msg.text.split(maxsplit=1)
    if len(args) == 1:
        return await msg.reply_text("Give Chat ID Also Where To Send Files")
    args=args[1]
    try:
        args=int(args)
    except Exception:
        return await msg.reply_text("Chat Id must be integer not string")
    jj=await msg.reply_text("Processing")
    documents=col.find({})
    last_msg=col.find({'_id':'last_msg'})
    if not last_msg:
        col.update_one({'_id':'last_msg'},{'$set':{'index':0}},upsert=True)
    id_list = [{'id': document['_id'], 'file_name': document['file_name'], 'file_caption': document['caption'] , 'file_size':document['file_size']} for document in documents]
    await jj.edit(f"Found {len(id_list)} Files In The DB Starting To Send In Chat {args}")
    for j , i in enumerate(id_list[last_msg:]):
        try:
            try:
                await app.send_video(msg.chat.id , i['id'] , caption=CUSTOM_FILE_CAPTION.format(file_name=i['file_name'] , file_caption=i['file_caption'] , file_size=i['file_size']))
                await jj.edit(f"Found {len(id_list)} Files In The DB Starting To Send In Chat {args}\nProcessed : {j+1}")
                col.update_one({'_id':'last_msg'},{'$set':{'index':j}},upsert=True)
                await asyncio.sleep(random.randint(8, 10))
                
            except Exception as e:
                print(e)
        except Exception:
            try:
                await app.send_document(msg.chat.id , i['id'] , caption=CUSTOM_FILE_CAPTION.format(file_name=i['file_name'] , file_caption=i['file_caption'] , file_size=i['file_size']))
                await jj.edit(f"Found {len(id_list)} Files In The DB Starting To Send In Chat {args}\nProcessed : {j+1}")
                col.update_one({'_id':'last_msg'},{'$set':{'index':j}},upsert=True)
                await asyncio.sleep(random.randint(8, 10))
            except Exception as e:
                print(e)
    await jj.delete()
    await msg.reply_text("completed")

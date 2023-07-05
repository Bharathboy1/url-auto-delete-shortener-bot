import pymongo
from pyrogram import Client, filters
from info import DATABASE_URI, DATABASE_NAME, COLLECTION_NAME, ADMINS, CHANNELS, CUSTOM_FILE_CAPTION
import asyncio
import random
import time
from pyrogram.errors import FloodWait

media_filter = filters.document | filters.video | filters.audio

myclient = pymongo.MongoClient(DATABASE_URI)
db = myclient[DATABASE_NAME]
col = db[COLLECTION_NAME]


def get_last_sent_message_from_database(channel_id):
    # Implement the database retrieval logic here
    # Retrieve and return the last sent message for the given channel_id
    return None  # Replace None with your actual last sent message retrieval logic

# Update the last sent message in the database for the specific channel
def update_last_sent_message_in_database(channel_id, last_sent_message_id):
    # Implement the database update logic here
    # Update the last sent message for the given channel_id with the provided last_sent_message_id
    pass
# Load last sent message index from database upon bot start/restart
#last_sent_message = load_last_sent_message_from_database()

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

async def save_file(media):
    # Implement your file-saving logic here
    pass

@Client.on_message(filters.command("savefile") & filters.user(ADMINS))
async def start(client, message):
    try:
        for file_type in ("document", "video", "audio"):
            media = getattr(message.reply_to_message, file_type, None)
            if media is not None:
                break
        else:
            return

        media.file_type = file_type
        media.caption = message.reply_to_message.caption
        await save_file(media)
        await message.reply_text("**Saved In DB**")
    except Exception as e:
        await message.reply_text(f"**Error: {str(e)}**")

@Client.on_message(filters.command("sendall") & filters.user(ADMINS))
async def send_all(app, msg):
    global last_sent_message  # Update last_sent_message as a global variable
    args = msg.text.split(maxsplit=1)
    if len(args) == 1:
        return await msg.reply_text("Give Chat ID Also Where To Send Files")
    args = args[1]
    try:
        args = int(args)
    except Exception:
        return await msg.reply_text("Chat Id must be an integer, not a string")
    jj = await msg.reply_text("Processing")
    
    # Get the last sent message for the specific channel from the database
    last_sent_message = get_last_sent_message_from_database(args)
    
    documents = col.find({"channel_id": args, "_id": {"$gt": last_sent_message["_id"]}})
    id_list = [{'id': document['_id'], 'file_name': document['file_name'], 'file_caption': document['caption'], 'file_size': document['file_size']} for document in documents]
    await jj.edit(f"Found {len(id_list)} Files In The DB Starting To Send In Chat {args}")
    
    for j, i in enumerate(id_list):
        try:
            try:
                await app.send_video(msg.chat.id, i['id'], caption=CUSTOM_FILE_CAPTION.format(file_name=i['file_name'], file_caption=i['file_caption'], file_size=i['file_size']))
            except FloodWait as e:
                time.sleep(e.x)
                await app.send_video(msg.chat.id, i['id'], caption=CUSTOM_FILE_CAPTION.format(file_name=i['file_name'], file_caption=i['file_caption'], file_size=i['file_size']))
        except Exception as e:
            print(e)

        await jj.edit(f"Found {len(id_list)} Files In The DB Starting To Send In Chat {args}\nProcessed: {j+1}")
        await asyncio.sleep(random.randint(5, 10))
        
        # Update the last sent message in the database
        update_last_sent_message_in_database(args, i['_id'])
    
    await jj.delete()
    await msg.reply_text("completed")

# Get the last sent message from the database for the specific channel


app = Client("my_bot")
app.run()


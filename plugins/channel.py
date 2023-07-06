import pymongo
from pyrogram import Client, filters
from info import DATABASE_URI, DATABASE_NAME, COLLECTION_NAME, ADMINS, CHANNELS, CUSTOM_FILE_CAPTION
from database.ia_filterdb import save_file
import asyncio
import random
from utils import get_size
import time
from pyrogram.errors.exceptions import FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

media_filter = filters.document | filters.video | filters.audio

myclient = pymongo.MongoClient(DATABASE_URI)
db = myclient[DATABASE_NAME]
col = db[COLLECTION_NAME]

pause_sending = False
confirm_reset = False
start_sending = False

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    """Media Handler"""
    if pause_sending:
        return
        
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
async def x(app, msg):
    global pause_sending,start_sending
    if not start_sending:
        await msg.reply_text("Please use the /resetsend command to start sending messages from the beginning.")
        
    
    args = msg.text.split(maxsplit=1)
    if len(args) == 1:
        return await msg.reply_text("Give Chat ID Also Where To Send Files")
    args = args[1]
    try:
        args = int(args)
    except Exception:
        return await msg.reply_text("Chat Id must be an integer not a string")
    jj = await msg.reply_text("Processing")
    documents = col.find({})
    last_msg = col.find_one({'_id': 'last_msg'})
    if not last_msg:
        col.update_one({'_id': 'last_msg'}, {'$set': {'index': 0}}, upsert=True)
        last_msg = 0
    else:
        last_msg = last_msg.get('index', 0)
    id_list = [{'id': document['_id'], 'file_name': document.get('file_name', 'N/A'), 'file_caption': document.get('caption', 'N/A'), 'file_size': document.get('file_size', 'N/A')} for document in documents]
    await jj.edit(f"Found {len(id_list)} Files In The DB Starting To Send In Chat {args}")
    for j, i in enumerate(id_list[last_msg:], start=last_msg):
        if j < last_msg:
            continue
 
        if pause_sending:
            await jj.edit("Sending paused. Use /resumesend to continue.")
            return
       
        try:
            try:
                await app.send_video(msg.chat.id, i['id'], caption=CUSTOM_FILE_CAPTION.format(file_name=i['file_name'], file_caption=i['file_caption'], file_size=get_size(int(i['file_size']))))
            except Exception as e:
                print(e)
                await app.send_document(msg.chat.id, i['id'], caption=CUSTOM_FILE_CAPTION.format(file_name=i['file_name'], file_caption=i['file_caption'], file_size=get_size(int(i['file_size']))))
            await jj.edit(f"Found {len(id_list)} Files In The DB Starting To Send In Chat {args}\nProcessed: {j+1}")
            col.update_one({'_id': 'last_msg'}, {'$set': {'index': j}}, upsert=True)
            await asyncio.sleep(random.randint(4,9))
        except FloodWait as e:
            # Handle "FloodWait" exception
            wait_time = e.x  # Get the wait time in seconds
            await jj.edit(f"Encountered 'FloodWait' exception. Waiting for {wait_time} seconds...")
            time.sleep(wait_time)
        except Exception as e:
            await jj.edit(f"Error: {str(e)}")
            break
    await jj.delete()
    await msg.reply_text("Completed")


@Client.on_message(filters.command("stopsend") & filters.user(ADMINS))
async def stop_sending(app, msg):
    global pause_sending  # Access the global flag
    pause_sending = True
    await msg.reply_text("Sending paused. Use /resumesend to continue.")

@Client.on_message(filters.command("resumesend") & filters.user(ADMINS))
async def resume_sending(app, msg):
    global pause_sending  # Access the global flag
    if pause_sending:
        pause_sending = False
        await msg.reply_text("Sending resumed.")
    else:
        await msg.reply_text("Sending is already in progress.")


@Client.on_message(filters.command("resetsend") & filters.user(ADMINS))
async def reset_sending(app, msg):
    global pause_sending, confirm_reset, start_sending

    if not start_sending:
        await msg.reply_text("Sending is already reset and ready to start from the beginning.")
        return

    if not confirm_reset:
        confirm_reset = True
        confirmation_markup = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("Confirm Reset", callback_data="confirm_reset"),
                InlineKeyboardButton("Cancel Reset", callback_data="cancel_reset")
            ]]
        )
        await msg.reply_text(
            "Are you sure you want to reset sending and start from the beginning?\n"
            "This action cannot be undone.",
            reply_markup=confirmation_markup
        )
    else:
        confirm_reset = False
        await msg.reply_text("Reset cancelled.")


@Client.on_callback_query()
async def handle_callback(app, callback_query):
    global pause_sending, confirm_reset, start_sending

    if callback_query.data == "confirm_reset":
        confirm_reset = False
        pause_sending = False
        start_sending = True
        await app.answer_callback_query(callback_query.id, "Sending reset. Messages will be sent from the beginning.")
    elif callback_query.data == "cancel_reset":
        confirm_reset = False
        await app.answer_callback_query(callback_query.id, "Reset cancelled.")


@Client.on_message(filters.command("sendlast") & filters.user(ADMINS))
async def send_last_messages(app, msg):
    try:
        count = int(msg.command[1])
    except (IndexError, ValueError):
        await msg.reply_text("Please provide a valid number for the count.")
        return
    
    documents = col.find({}).sort("_id", -1).limit(count)
    id_list = [
        {
            'id': document['_id'],
            'file_name': document.get('file_name', 'N/A'),
            'file_caption': document.get('caption', 'N/A'),
            'file_size': document.get('file_size', '00')
        } 
        for document in documents
    ]
    
    for j, i in enumerate(id_list):
        try:
            try:
                await app.send_video(
                    msg.chat.id,
                    i['id'],
                    caption=CUSTOM_FILE_CAPTION.format(
                        file_name=i['file_name'],
                        file_caption=i['file_caption'],
                        file_size=get_size(int(i['file_size']))
                    )
                )
            except Exception as e:
                print(e)
                await app.send_document(
                    msg.chat.id,
                    i['id'],
                    caption=CUSTOM_FILE_CAPTION.format(
                        file_name=i['file_name'],
                        file_caption=i['file_caption'],
                        file_size=get_size(int(i['file_size']))
                    )
                )
            
            await asyncio.sleep(random.randint(4,8))
        except FloodWait as e:
            print(f"Sleeping for {e.x} seconds.")
            await asyncio.sleep(e.x)
        except Exception as e:
            print(e)
            #await jj.delete()
            await msg.reply_text("An error occurred while sending messages.")
            break
    
    await msg.reply_text("Completed")



@Client.on_message(filters.command("sendkey") & filters.user(ADMINS))
async def send_messages_with_keyword(app, msg):
    try:
        keywords = msg.command[1].split("-")
    except IndexError:
        await msg.reply_text("Please provide keyword(s) to search for in the file names.")
        return
    regex_pattern = "|".join(keywords)
    documents = col.find({"file_name": {"$regex": '|'.join(keywords)}})
    
    id_list = [
        {
            'id': document['_id'],
            'file_name': document.get('file_name', 'N/A'),
            'file_caption': document.get('caption', 'N/A'),
            'file_size': document.get('file_size', 'N/A')
        } 
        for document in documents
    ]
    
    for j, i in enumerate(id_list):
        try:
            try:
                await app.send_video(
                    msg.chat.id,
                    i['id'],
                    caption=CUSTOM_FILE_CAPTION.format(
                        file_name=i['file_name'],
                        file_caption=i['file_caption'],
                        file_size=get_size(int(i['file_size']))
                    )
                )
            except Exception as e:
                print(e)
                await app.send_document(
                    msg.chat.id,
                    i['id'],
                    caption=CUSTOM_FILE_CAPTION.format(
                        file_name=i['file_name'],
                        file_caption=i['file_caption'],
                        file_size=get_size(int(i['file_size']))
                    )
                )
            
            await asyncio.sleep(random.randint(4,8))
        except FloodWait as e:
            print(f"Sleeping for {e.x} seconds.")
            await asyncio.sleep(e.x)
        except Exception as e:
            print(e)
            await jj.delete()
            await msg.reply_text("An error occurred while sending messages.")
            break
    
    await msg.reply_text("Completed")

# Run the bot



#app.run()

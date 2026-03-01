from telethon import TelegramClient, events
from telethon.tl import functions, types
import re
import requests
from bs4 import BeautifulSoup
import asyncio
import os
import logging
import sys
import random
import hashlib
import aiohttp
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import database modules
sys.path.append(os.path.dirname(__file__))
from database import bot as db_bot
from database import users as db_users
from database import stok as db_stok
from database import gacha as gacha_db
import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ KONFIGURASI ============
OWNER_IDS_STR = os.getenv('OWNER_IDS', '7998861975')
OWNER_ID = [int(id.strip()) for id in OWNER_IDS_STR.split(',')]

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH')
WEBSITE_URL = os.getenv('WEBSITE_URL', 'http://localhost:8000')
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
API_KEY = hashlib.sha256(SECRET_KEY.encode()).hexdigest()[:16]

if not all([BOT_TOKEN, API_ID, API_HASH]):
    logger.error("❌ Konfigurasi bot tidak lengkap. Pastikan .env sudah benar.")
    sys.exit(1)

# ============ FUNGSI UTILITY ============
def process_message(text):
    lines = text.splitlines()
    valid_usernames = [line.split()[0] for line in lines if "✅" in line]
    if not valid_usernames:
        return "Tidak ada username yang valid."
    return ", ".join(valid_usernames)

def is_valid_username(username):
    return re.match(r'^[a-zA-Z0-9_]{5,32}$', username)

async def check_telegram_username(client, username):
    try:
        await client.get_entity(username)
        return "user"
    except ValueError:
        return "available"
    except Exception as e:
        logger.error(f"Error checking username {username}: {e}")
        return None

def check_fragment_username(username):
    url = f"https://fragment.com/?filter={username}"
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        if soup.find(string=username):
            return "fragment"
    except Exception as e:
        logger.error(f"Error fetching fragment: {e}")
    return None

async def check_username_status(client, username):
    if not is_valid_username(username):
        return f"@{username} (invalid)"
    
    telegram_status = await check_telegram_username(client, username)
    if telegram_status == "user":
        return f"@{username} (user)"
    elif telegram_status == "available":
        fragment_status = check_fragment_username(username)
        if fragment_status:
            return f"@{username} (fragment)"
        return f"@{username} (✅)"
    return f"@{username} (❓)"

async def check_multiple_usernames(client, usernames):
    results = await asyncio.gather(*(check_username_status(client, username) for username in usernames))
    return "\n".join(results)

def generate_variations(word):
    alphabet = 'abcdefghijklmnopqrstuvwxyz'
    grouped_results = []
    for pos in range(len(word) + 1):
        group = []
        for letter in alphabet:
            new_word = '@' + word[:pos] + letter + word[pos:]
            group.append(new_word)
        grouped_results.append(", ".join(group))
    return grouped_results

# ============ FUNGSI DEPOSIT ============
async def notify_website_payment_success(charge_id, payload, user_id, amount):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{WEBSITE_URL}/gacha/api/deposit/verify", json={
                'charge_id': charge_id,
                'payload': payload,
                'user_id': user_id,
                'amount': amount,
                'api_key': API_KEY
            }) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Website notification sent: {result}")
                    return True
                else:
                    logger.error(f"❌ Failed to notify website: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Error notifying website: {e}")
        return False

# ============ FUNGSI UTAMA BOT ============
async def run_bot(config):
    session_name = f"session_{config['bot_token'].split(':')[0]}"
    client = TelegramClient(session_name, config['api_id'], config['api_hash'])
    
    # Dictionary untuk menyimpan transaksi sementara (per client)
    temp_transactions = {}
    
    try:
        await client.start(bot_token=config['bot_token'])
        logger.info(f"Bot started with token: {config['bot_token'][:10]}...")
        
        me = await client.get_me()
        db_bot.update_bot_info(config['bot_token'], me.username, str(me.id))
        
        bot_type = "🔵 BOT UTAMA" if config.get('is_main') else "🟢 BOT CLONE"
        print(f"\n{'='*50}")
        print(f"{bot_type} BERHASIL JALAN!")
        print(f"Username: @{me.username}")
        print(f"Bot ID: {me.id}")
        print(f"{'='*50}\n")

        # ============ HANDLER UNTUK START (DENGAN PAYMENT LINK) ============
        @client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            """Handle /start command with payload parameter"""
            
            # Parse parameter jika ada
            if event.message.text.startswith('/start '):
                payload = event.message.text[7:].strip()  # Ambil setelah /start 
                
                # Cek apakah ini link payment (format: $random_string)
                if payload.startswith('$'):
                    # Ini adalah payment link dari gacha system
                    link_id = payload[1:]  # Hapus karakter $
                    await handle_payment_link(event, link_id)
                    return
                
                elif payload.startswith('deposit:'):
                    # Ini adalah request deposit (format lama)
                    await handle_deposit_payload(event, payload)
                    return
            
            # Default response
            await event.respond(
                "🤖 **Bot Gacha Username**\n\n"
                "Bot ini digunakan untuk memproses pembayaran deposit dari website.\n\n"
                f"🌐 **Website:** {WEBSITE_URL}\n"
                f"💰 **Deposit:** Minimal 1 Stars\n\n"
                "Silakan lakukan deposit melalui website untuk mendapatkan saldo.\n\n"
                "📝 **Test Deposit:** /deposit <jumlah>"
            )

        async def handle_payment_link(event, link_id):
            """Handle payment link dari gacha system"""
            try:
                logger.info(f"Payment link clicked: {link_id}")
                
                # Dapatkan payload dari database berdasarkan link_id
                link_data = gacha_db.get_payload_from_link(link_id)
                
                if not link_data:
                    await event.respond(
                        "❌ **Link pembayaran tidak valid atau sudah kadaluarsa.**\n\n"
                        "Silakan buat deposit baru melalui website."
                    )
                    return
                
                payload = link_data['payload']
                trans_id = link_data['transaction_id']
                
                # Parse payload: deposit:user_id:amount:timestamp:random
                if payload.startswith('deposit:'):
                    parts = payload.split(':')
                    if len(parts) == 5:
                        user_id = int(parts[1])
                        amount = int(parts[2])
                        
                        # Validasi user
                        if event.sender_id != user_id:
                            await event.respond(
                                "❌ **User tidak sesuai.**\n\n"
                                "Link ini khusus untuk user dengan ID yang berbeda."
                            )
                            return
                        
                        # Simpan di temp_transactions (seperti di pay.py)
                        temp_transactions[payload] = {
                            'user_id': user_id,
                            'amount': amount,
                            'transaction_id': trans_id,
                            'status': 'pending',
                            'created_at': datetime.now().isoformat()
                        }
                        
                        # Kirim invoice Stars
                        await send_stars_invoice(event, amount, payload)
                        return
                
                await event.respond("❌ Format payload tidak valid.")
                
            except Exception as e:
                logger.error(f"Error handling payment link: {e}")
                await event.respond("❌ Terjadi kesalahan. Silakan coba lagi.")

        async def handle_deposit_payload(event, payload):
            """Handle deposit payload (format lama)"""
            try:
                parts = payload.split(':')
                if len(parts) == 5:
                    user_id = int(parts[1])
                    amount = int(parts[2])
                    
                    if event.sender_id != user_id:
                        await event.respond("❌ User ID tidak sesuai dengan transaksi")
                        return
                    
                    # Simpan di temp_transactions
                    temp_transactions[payload] = {
                        'user_id': user_id,
                        'amount': amount,
                        'status': 'pending',
                        'created_at': datetime.now().isoformat()
                    }
                    
                    # Kirim invoice untuk pembayaran Stars
                    await send_stars_invoice(event, amount, payload)
                    return
            except Exception as e:
                logger.error(f"Error handling deposit payload: {e}")
                await event.respond("❌ Terjadi kesalahan.")

        async def send_stars_invoice(event, amount, payload):
            """Kirim invoice Stars ke user (seperti di pay.py)"""
            try:
                logger.info(f"Sending invoice for {amount} stars with payload: {payload}")
                
                invoice = types.Invoice(
                    currency="XTR",  # Telegram Stars
                    prices=[types.LabeledPrice(
                        label=f"Deposit {amount} Stars",
                        amount=amount
                    )]
                )
                
                media = types.InputMediaInvoice(
                    title="💰 Deposit Stars",
                    description=f"Deposit {amount} ⭐ ke saldo Gacha Username",
                    photo=None,
                    invoice=invoice,
                    payload=payload.encode(),
                    provider=None,
                    provider_data=types.DataJSON(data='{}'),
                    start_param="deposit"
                )
                
                await event.client(functions.messages.SendMediaRequest(
                    peer=await event.client.get_input_entity(event.chat_id),
                    media=media,
                    message=f"🧾 **INVOICE DEPOSIT**\n\n"
                            f"Jumlah: **{amount} ⭐**\n\n"
                            f"Klik tombol **PAY {amount} ⭐** di bawah untuk membayar.",
                    random_id=random.randint(1, 2**63)
                ))
                
                logger.info(f"Invoice sent to user {event.sender_id} for {amount} stars")
                
            except Exception as e:
                logger.error(f"Error sending invoice: {e}")
                await event.respond(f"❌ Gagal mengirim invoice: {str(e)}")

        # ============ HANDLER UNTUK RAW PAYMENT (PRE-CHECKOUT & SUCCESS) ============
        @client.on(events.Raw)
        async def raw_payment_handler(event):
            """Handler untuk semua raw updates (seperti di pay.py)"""
            
            # HANDLE PRE-CHECKOUT QUERY
            if isinstance(event, types.UpdateBotPrecheckoutQuery):
                query_id = event.query_id
                user_id = event.user_id
                payload = event.payload.decode() if event.payload else ""
                currency = event.currency
                total_amount = event.total_amount
                
                logger.info(f"💰 PRE-CHECKOUT: User {user_id}, Amount {total_amount} {currency}, Payload: {payload}")
                
                try:
                    # Validasi currency
                    if currency != 'XTR':
                        await event.client(functions.messages.SetBotPrecheckoutResultsRequest(
                            query_id=query_id,
                            success=False,
                            error="Hanya menerima Telegram Stars"
                        ))
                        return
                    
                    # Cek di temp_transactions dulu
                    if payload in temp_transactions:
                        trans = temp_transactions[payload]
                        
                        # Validasi user
                        if trans['user_id'] != user_id:
                            await event.client(functions.messages.SetBotPrecheckoutResultsRequest(
                                query_id=query_id,
                                success=False,
                                error="User tidak sesuai"
                            ))
                            return
                        
                        # Validasi jumlah
                        if total_amount != trans['amount']:
                            await event.client(functions.messages.SetBotPrecheckoutResultsRequest(
                                query_id=query_id,
                                success=False,
                                error="Jumlah tidak sesuai"
                            ))
                            return
                        
                        # APPROVE
                        await event.client(functions.messages.SetBotPrecheckoutResultsRequest(
                            query_id=query_id,
                            success=True
                        ))
                        logger.info(f"✅ Pre-checkout approved for user {user_id} (from temp)")
                        temp_transactions[payload]['pre_checkout_approved'] = True
                        return
                    
                    # Cek di database
                    if payload.startswith('deposit:'):
                        parts = payload.split(':')
                        if len(parts) == 5:
                            user_id_from_payload = int(parts[1])
                            amount_from_payload = int(parts[2])
                            
                            if user_id_from_payload != user_id:
                                await event.client(functions.messages.SetBotPrecheckoutResultsRequest(
                                    query_id=query_id,
                                    success=False,
                                    error="User mismatch"
                                ))
                                return
                            
                            if total_amount != amount_from_payload:
                                await event.client(functions.messages.SetBotPrecheckoutResultsRequest(
                                    query_id=query_id,
                                    success=False,
                                    error="Amount mismatch"
                                ))
                                return
                            
                            trans = gacha_db.get_pending_deposit(payload)
                            if not trans:
                                await event.client(functions.messages.SetBotPrecheckoutResultsRequest(
                                    query_id=query_id,
                                    success=False,
                                    error="Transaction expired"
                                ))
                                return
                            
                            # APPROVE
                            await event.client(functions.messages.SetBotPrecheckoutResultsRequest(
                                query_id=query_id,
                                success=True
                            ))
                            logger.info(f"✅ Pre-checkout approved for user {user_id} (from DB)")
                            return
                    
                    # Jika tidak ditemukan
                    await event.client(functions.messages.SetBotPrecheckoutResultsRequest(
                        query_id=query_id,
                        success=False,
                        error="Transaksi tidak valid"
                    ))
                    
                except Exception as e:
                    logger.error(f"Error in pre-checkout: {e}")
                    try:
                        await event.client(functions.messages.SetBotPrecheckoutResultsRequest(
                            query_id=query_id,
                            success=False,
                            error="Terjadi kesalahan sistem"
                        ))
                    except:
                        pass
            
            # HANDLE SUCCESSFUL PAYMENT
            elif isinstance(event, types.UpdateNewMessage):
                message = event.message
                
                if not message or not hasattr(message, 'action'):
                    return
                
                if isinstance(message.action, types.MessageActionPaymentSentMe):
                    try:
                        payment = message.action
                        user_id = message.peer_id.user_id
                        currency = payment.currency
                        total_amount = payment.total_amount
                        payload = payment.payload.decode() if payment.payload else ""
                        charge_id = payment.charge.id
                        
                        logger.info(f"🎉 PAYMENT SUCCESS! User {user_id}, Charge ID {charge_id}, Amount {total_amount} {currency}")
                        
                        # Kirim notifikasi ke website
                        if payload.startswith('deposit:'):
                            # Cek di temp_transactions dulu
                            if payload in temp_transactions:
                                logger.info(f"Payment from temp transaction: {payload}")
                                del temp_transactions[payload]
                            
                            # Verifikasi ke website
                            success = await notify_website_payment_success(
                                charge_id=charge_id,
                                payload=payload,
                                user_id=user_id,
                                amount=total_amount
                            )
                            
                            if success:
                                await event.client.send_message(
                                    user_id,
                                    f"✅ **DEPOSIT BERHASIL!**\n\n"
                                    f"💰 Jumlah: {total_amount} ⭐\n"
                                    f"🆔 Transaksi: `{charge_id}`\n\n"
                                    f"Saldo Anda telah bertambah. Silakan kembali ke website.\n\n"
                                    f"🌐 {WEBSITE_URL}"
                                )
                            else:
                                # Coba lagi nanti atau manual
                                await event.client.send_message(
                                    user_id,
                                    f"✅ **PEMBAYARAN DITERIMA!**\n\n"
                                    f"💰 Jumlah: {total_amount} ⭐\n"
                                    f"🆔 Transaksi: `{charge_id}`\n\n"
                                    f"Sedang memproses penambahan saldo. Silakan tunggu beberapa saat.\n"
                                    f"Jika saldo tidak bertambah dalam 5 menit, hubungi admin."
                                )
                            
                            logger.info(f"✅ Payment processed for user {user_id}: {total_amount} stars")
                        
                    except Exception as e:
                        logger.error(f"Error processing payment: {e}")
                        import traceback
                        traceback.print_exc()

        # ============ HANDLER UNTUK TEST DEPOSIT ============
        @client.on(events.NewMessage(pattern='/deposit'))
        async def deposit_test_handler(event):
            """Handler untuk test deposit via command"""
            try:
                # Parse jumlah
                parts = event.message.text.split()
                if len(parts) != 2:
                    await event.respond(
                        "❌ **Format salah!**\n\n"
                        "Gunakan: `/deposit <jumlah>`\n"
                        "Contoh: `/deposit 10`"
                    )
                    return
                
                try:
                    amount = int(parts[1])
                    if amount < 1:
                        await event.respond("❌ Jumlah minimal 1 ⭐")
                        return
                    if amount > 2500:
                        await event.respond("❌ Maksimal 2500 ⭐")
                        return
                except ValueError:
                    await event.respond("❌ Jumlah harus angka")
                    return
                
                # Generate payload untuk test
                user_id = event.sender_id
                timestamp = int(datetime.now().timestamp())
                random_code = random.randint(1000, 9999)
                payload = f"deposit:{user_id}:{amount}:{timestamp}:{random_code}"
                
                # Simpan di temp_transactions
                temp_transactions[payload] = {
                    'user_id': user_id,
                    'amount': amount,
                    'status': 'pending',
                    'created_at': datetime.now().isoformat(),
                    'test_mode': True
                }
                
                # Kirim invoice
                await send_stars_invoice(event, amount, payload)
                
            except Exception as e:
                logger.error(f"Error in deposit_test_handler: {e}")
                await event.respond(f"❌ Error: {str(e)}")

        # ============ HANDLER UNTUK BALANCE (VERSI YANG BENAR) ============
        @client.on(events.NewMessage(pattern='/balance'))
        async def balance_handler(event):
            """Cek saldo Stars bot"""
            if event.sender_id not in OWNER_ID:
                await event.respond("❌ Perintah ini hanya untuk owner")
                return
            
            try:
                # Method yang benar untuk cek saldo Stars
                result = await client(functions.payments.GetStarsStatusRequest(
                    peer=await client.get_input_entity('me')
                ))
                
                balance = result.balance
                
                # Format response
                await event.respond(
                    f"💰 **SALDO BOT STARS**\n\n"
                    f"**{balance}** ⭐\n\n"
                    f"📌 Update: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                )
                
            except Exception as e:
                logger.error(f"Error in balance_handler: {e}")
                
                # Coba method alternatif
                try:
                    result = await client(functions.payments.GetStarsBalanceRequest())
                    balance = result.balance
                    await event.respond(f"💰 **SALDO BOT STARS:** {balance} ⭐")
                except:
                    await event.respond(f"❌ Gagal mendapatkan saldo: {str(e)}")

        # ============ HANDLER LAINNYA ============
        @client.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            if event.sender_id not in OWNER_ID:
                return
            
            help_text = "**PERINTAH YANG TERSEDIA:**\n\n"
            help_text += "/edit <kata> - Buat variasi username\n"
            help_text += "/check <username> - Cek ketersediaan username\n"
            help_text += "/ubah <teks> - Proses hasil check\n"
            help_text += "/balance - Cek saldo Stars bot\n"
            help_text += "/deposit <jumlah> - Test deposit Stars\n"
            
            if config.get('is_main'):
                help_text += "\n**PERINTAH BOT UTAMA:**\n"
                help_text += "/clone - Tambah bot clone\n"
                help_text += "/listbots - Lihat daftar bot\n"
                help_text += "/delbot <token> - Hapus bot clone\n"
                help_text += "/totalbots - Statistik bot\n"
            
            await event.respond(help_text)

        @client.on(events.NewMessage(pattern='/ubah'))
        async def ubah_handler(event):
            if event.sender_id not in OWNER_ID:
                return
            
            user_input = event.message.text.split('/ubah', maxsplit=1)[1].strip()
            if user_input:
                result = process_message(user_input)
                if result:
                    if "✅" in result:
                        lines = result.split('\n')
                        available = []
                        for line in lines:
                            if "✅" in line:
                                username = line.split()[0].replace('@', '')
                                available.append(f"@{username}")
                        if available:
                            db_stok.add_usernames(', '.join(available))
                    
                    await event.respond(f"`/check {result}`")
                else:
                    await event.respond("Tidak ada username valid ditemukan.")
            else:
                await event.respond("Format salah. Gunakan: /ubah <teks>.")

        @client.on(events.NewMessage(pattern='/check'))
        async def check_handler(event):
            if event.sender_id not in OWNER_ID:
                return
            
            user_input = event.message.text.split('/check', maxsplit=1)[1].strip()
            usernames = [u.strip('@ ') for u in user_input.split(',')]
            result = await check_multiple_usernames(client, usernames)
            
            if result:
                await event.respond(f"`/ubah {result}`")
            else:
                await event.respond("Tidak ada username valid.")

        @client.on(events.NewMessage(pattern='/edit'))
        async def edit_handler(event):
            if event.sender_id not in OWNER_ID:
                return
        
            text = event.message.text.split(' ', 1)
            if len(text) < 2:
                await event.reply('Kirimkan format: /edit <kata>')
                return
        
            word = text[1]
            variations = generate_variations(word)
            all_variations = ", ".join(variations)
        
            try:
                if len(all_variations) > 4096:
                    chunks = [all_variations[i:i+4096] for i in range(0, len(all_variations), 4096)]
                    for chunk in chunks:
                        await event.reply(chunk)
                else:
                    await event.reply(f"`/check {all_variations}`")
            except Exception as e:
                logger.error(f"Error: {e}")

        # HANDLER KHUSUS BOT UTAMA
        if config.get('is_main'):
            @client.on(events.NewMessage(pattern='/clone'))
            async def clone_handler(event):
                if event.sender_id not in OWNER_ID:
                    return
                
                if not event.message.is_reply:
                    await event.reply("Silakan reply ke pesan yang berisi format API ID, API HASH, dan BOT_TOKEN")
                    return
                
                replied = await event.get_reply_message()
                text = replied.text
                
                api_id_match = re.search(r'API_ID:\s*(\d+)', text)
                api_hash_match = re.search(r'API_HASH:\s*(\w+)', text)
                bot_token_match = re.search(r'BOT_TOKEN:\s*([\w:]+)', text)
                
                if not all([api_id_match, api_hash_match, bot_token_match]):
                    await event.reply("Format tidak valid. Gunakan format:\nAPI_ID: 1234567890\nAPI_HASH: AnoNO61bJ7...\nBOT_TOKEN: 1234567890:Bai17bJab...")
                    return
                
                api_id = api_id_match.group(1)
                api_hash = api_hash_match.group(1)
                bot_token = bot_token_match.group(1)
                
                if db_bot.save_bot(api_id, api_hash, bot_token, is_main=False):
                    await event.reply(f"✅ Bot clone berhasil ditambahkan. Restarting...")
                    os._exit(0)
                else:
                    await event.reply("❌ Bot dengan token tersebut sudah ada")

            @client.on(events.NewMessage(pattern='/listbots'))
            async def list_bots_handler(event):
                if event.sender_id not in OWNER_ID:
                    return
                
                bots = db_bot.get_all_bots()
                if not bots:
                    await event.reply("Tidak ada bot yang terdaftar")
                    return
                
                message = "**📋 DAFTAR BOT:**\n\n"
                for i, bot in enumerate(bots, 1):
                    bot_type = "🔵 BOT UTAMA" if bot['is_main'] else "🟢 BOT CLONE"
                    message += f"{i}. {bot_type}\n"
                    message += f"   👤 @{bot['username'] or 'Unknown'}\n"
                    message += f"   🆔 ID: {bot['bot_id'] or 'Unknown'}\n"
                    message += f"   🔑 Token: {bot['bot_token'][:15]}...\n\n"
                
                await event.reply(message)

            @client.on(events.NewMessage(pattern='/delbot'))
            async def delete_bot_handler(event):
                if event.sender_id not in OWNER_ID:
                    return
                
                args = event.message.text.split()
                if len(args) != 2:
                    await event.reply("Gunakan: /delbot <token_awal_bot>")
                    return
                
                token_prefix = args[1]
                bots = db_bot.get_all_bots()
                
                bot_to_delete = None
                for bot in bots:
                    if bot['bot_token'].startswith(token_prefix) and not bot['is_main']:
                        bot_to_delete = bot
                        break
                
                if not bot_to_delete:
                    await event.reply("❌ Bot tidak ditemukan")
                    return
                
                if db_bot.delete_bot(bot_to_delete['bot_token']):
                    await event.reply(f"✅ Bot @{bot_to_delete.get('username', 'Unknown')} telah dihapus. Restarting...")
                    os._exit(0)
                else:
                    await event.reply("❌ Gagal menghapus bot")

            @client.on(events.NewMessage(pattern='/totalbots'))
            async def total_bots_handler(event):
                if event.sender_id not in OWNER_ID:
                    return
                stats = db_bot.get_bot_stats()
                await event.reply(f"📊 **STATISTIK BOT:**\n\n🔵 Bot Utama: {stats['main']}\n🟢 Bot Clone: {stats['clone']}\n📌 Total: {stats['total']}")

        print(f"✅ Semua handler untuk @{me.username} telah terdaftar!")
        await client.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"Error pada bot: {e}")
    finally:
        await client.disconnect()

async def main():
    print("🚀 Memulai bot...")
    print(f"📌 Website URL: {WEBSITE_URL}")
    print(f"📌 Owner IDs: {OWNER_ID}")
    
    all_configs = db_bot.load_bot_configs()
    
    if not all_configs:
        print("📌 Tidak ada bot dalam database. Menjalankan bot utama...")
        main_config = {
            'api_id': API_ID,
            'api_hash': API_HASH,
            'bot_token': BOT_TOKEN,
            'is_main': True,
            'username': None,
            'bot_id': None
        }
        await run_bot(main_config)
    else:
        print(f"📌 Menjalankan {len(all_configs)} bot...")
        tasks = [asyncio.create_task(run_bot(config)) for config in all_configs]
        await asyncio.gather(*tasks)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Program dihentikan oleh user.")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
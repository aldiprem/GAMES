import os
import sys
import asyncio
import logging
import random
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button
from telethon.tl import types, functions
import pytz

# Tambahkan path ke direktori saat ini
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Database imports
try:
    from py.gacha import SessionLocal, User, Transaction, get_wib_time, engine, Base
except ImportError:
    # Fallback jika struktur folder berbeda
    from gacha import SessionLocal, User, Transaction, get_wib_time, engine, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

bot = TelegramClient('stdeposit', API_ID, API_HASH)

# Timezone Indonesia
WIB = pytz.timezone('Asia/Jakarta')

def get_wib_time():
    return datetime.now(WIB)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    # Simpan user ke database jika belum ada
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == event.sender_id).first()
        if not user:
            user = User(
                telegram_id=event.sender_id,
                username=event.sender.username,
                first_name=event.sender.first_name,
                last_name=event.sender.last_name
            )
            db.add(user)
            db.commit()
    finally:
        db.close()
    
    await event.respond(
        "💰 **Selamat Datang di Deposit Bot** 💰\n\n"
        "Bot ini menerima deposit menggunakan **Telegram Stars** ⭐\n\n"
        "**Cara Deposit:**\n"
        "Ketik: `/deposit <jumlah_stars>`\n"
        "Contoh: `/deposit 2`\n\n"
        "**Website:**\n"
        f"• Kunjungi {WEBHOOK_URL} untuk cek saldo"
    )

@bot.on(events.NewMessage(pattern='/deposit'))
async def deposit_handler(event):
    try:
        command = event.message.text.split()
        if len(command) != 2:
            await event.respond("❌ Format: `/deposit <jumlah>`")
            return
        
        amount = int(command[1])
        if amount <= 0 or amount > 2500:
            await event.respond("❌ Jumlah tidak valid (1-2500)")
            return
        
        user_id = event.sender_id
        timestamp = int(get_wib_time().timestamp())
        
        # Buat payload unik
        payload = f"deposit:{user_id}:{amount}:{random.randint(1000, 9999)}:{timestamp}"
        
        # Simpan ke database
        db = SessionLocal()
        try:
            # Dapatkan user
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                user = User(
                    telegram_id=user_id,
                    username=event.sender.username,
                    first_name=event.sender.first_name,
                    last_name=event.sender.last_name
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            
            # Buat transaksi
            transaction = Transaction(
                user_id=user.id,
                amount=amount,
                payload=payload,
                status='pending',
                created_at=get_wib_time()
            )
            db.add(transaction)
            db.commit()
        finally:
            db.close()
        
        # Panggil Bot API untuk createInvoiceLink
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink"
        
        data = {
            "title": f"Deposit {amount} Stars",
            "description": f"Deposit {amount} Telegram Stars",
            "payload": payload,
            "currency": "XTR",
            "prices": [{"label": f"Deposit {amount} ⭐", "amount": amount}],
            "provider_token": ""
        }
        
        response = requests.post(url, json=data)
        result = response.json()
        
        if result.get("ok"):
            invoice_link = result["result"]
            
            buttons = [[Button.url(f"💳 Bayar {amount} ⭐", invoice_link)]]
            
            await event.respond(
                f"🧾 **LINK DEPOSIT**\n\n"
                f"💰 Jumlah: `{amount}` Stars\n\n"
                f"Klik tombol di bawah untuk membayar:",
                buttons=buttons
            )
        else:
            await event.respond(f"❌ Gagal: {result.get('description')}")
        
    except Exception as e:
        logger.error(f"Error in deposit_handler: {e}")
        await event.respond("❌ Terjadi kesalahan")

@bot.on(events.Raw)
async def raw_handler(event):
    # HANDLE PRE-CHECKOUT QUERY
    if isinstance(event, types.UpdateBotPrecheckoutQuery):
        query_id = event.query_id
        user_id = event.user_id
        payload = event.payload.decode() if event.payload else ""
        currency = event.currency
        total_amount = event.total_amount
        
        logger.info(f"Pre-checkout received: User {user_id}, Amount {total_amount} {currency}, Payload {payload}")
        
        db = SessionLocal()
        try:
            # Cari transaksi di database
            transaction = db.query(Transaction).filter(Transaction.payload == payload).first()
            
            if not transaction:
                await bot(functions.messages.SetBotPrecheckoutResultsRequest(
                    query_id=query_id,
                    success=False,
                    error="Transaksi tidak valid"
                ))
                return
            
            # Load user relationship
            user = db.query(User).filter(User.id == transaction.user_id).first()
            
            if user.telegram_id != user_id:
                await bot(functions.messages.SetBotPrecheckoutResultsRequest(
                    query_id=query_id,
                    success=False,
                    error="User tidak sesuai"
                ))
                return
            
            if currency != 'XTR' or total_amount != transaction.amount:
                await bot(functions.messages.SetBotPrecheckoutResultsRequest(
                    query_id=query_id,
                    success=False,
                    error="Jumlah tidak sesuai"
                ))
                return
            
            # APPROVE
            await bot(functions.messages.SetBotPrecheckoutResultsRequest(
                query_id=query_id,
                success=True
            ))
            
            logger.info(f"Pre-checkout approved for payload {payload}")
            
        except Exception as e:
            logger.error(f"Error in pre_checkout: {e}")
            try:
                await bot(functions.messages.SetBotPrecheckoutResultsRequest(
                    query_id=query_id,
                    success=False,
                    error="Terjadi kesalahan sistem"
                ))
            except:
                pass
        finally:
            db.close()
    
    # HANDLE SUCCESSFUL PAYMENT
    elif isinstance(event, types.UpdateNewMessage):
        message = event.message
        
        if not message or not hasattr(message, 'action'):
            return
        
        if isinstance(message.action, types.MessageActionPaymentSentMe):
            try:
                payment = message.action
                user_id = message.peer_id.user_id
                payload = payment.payload.decode() if payment.payload else ""
                charge_id = payment.charge.id
                total_amount = payment.total_amount
                
                logger.info(f"PAYMENT SUCCESS! User {user_id}, Charge ID {charge_id}")
                
                db = SessionLocal()
                try:
                    # Cari transaksi
                    transaction = db.query(Transaction).filter(Transaction.payload == payload).first()
                    
                    if transaction and transaction.status == 'pending':
                        # Update transaksi
                        transaction.status = 'completed'
                        transaction.charge_id = charge_id
                        transaction.completed_at = get_wib_time()
                        
                        # Update saldo user
                        user = db.query(User).filter(User.id == transaction.user_id).first()
                        if user:
                            user.balance += total_amount
                        
                        db.commit()
                        
                        # Kirim konfirmasi
                        waktu = get_wib_time().strftime('%d/%m/%Y %H:%M:%S')
                        await bot.send_message(
                            user_id,
                            f"✅ **DEPOSIT BERHASIL!**\n\n"
                            f"💰 **Jumlah:** {total_amount} ⭐\n"
                            f"🆔 **Transaksi:** `{charge_id}`\n"
                            f"📅 **Waktu:** {waktu}\n\n"
                            f"Terima kasih telah melakukan deposit! 🎉"
                        )
                        
                        logger.info(f"Deposit completed for user {user_id}")
                finally:
                    db.close()
                
            except Exception as e:
                logger.error(f"Error processing payment: {e}")

@bot.on(events.NewMessage(pattern='/balance'))
async def balance_handler(event):
    admin_ids = [7998861975]
    
    if event.sender_id not in admin_ids:
        await event.respond("❌ Perintah ini hanya untuk admin")
        return
    
    try:
        result = await bot(functions.payments.GetStarsBalanceRequest())
        balance = result.balance
        
        await event.respond(f"💰 **SALDO BOT:** `{balance}` ⭐")
        
    except Exception as e:
        logger.error(f"Error in balance_handler: {e}")
        await event.respond("❌ Gagal mendapatkan saldo")

@bot.on(events.NewMessage(pattern='/stats'))
async def stats_handler(event):
    admin_ids = [7998861975]
    
    if event.sender_id not in admin_ids:
        await event.respond("❌ Perintah ini hanya untuk admin")
        return
    
    db = SessionLocal()
    try:
        total_users = db.query(User).count()
        total_transactions = db.query(Transaction).filter(Transaction.status == 'completed').count()
        total_stars = db.query(Transaction).filter(Transaction.status == 'completed').with_entities(db.func.sum(Transaction.amount)).scalar() or 0
        pending = db.query(Transaction).filter(Transaction.status == 'pending').count()
    finally:
        db.close()
    
    await event.respond(
        f"📊 **STATISTIK**\n\n"
        f"👥 Total User: {total_users}\n"
        f"✅ Transaksi Sukses: {total_transactions}\n"
        f"💰 Total Stars: {total_stars} ⭐\n"
        f"⏳ Pending: {pending}"
    )

@bot.on(events.NewMessage(pattern='/refund'))
async def refund_handler(event):
    """
    Refund deposit Stars
    Format: /refund <user_id> <telegram_payment_charge_id>
    """
    admin_ids = [7998861975]  # ID owner bot
    
    if event.sender_id not in admin_ids:
        await event.respond("❌ Perintah ini hanya untuk owner bot")
        return
    
    parts = event.message.text.split()
    if len(parts) != 3:
        await event.respond(
            "📌 **Cara Refund:**\n"
            "`/refund <user_id> <telegram_payment_charge_id>`\n\n"
            "Contoh:\n"
            "`/refund 7998861975 stxWMsESZh95IM-lsM8wEYqzsRSaRbYrISfS3lOK9ZLW9ZP53KKc2jia_YGOHzWglVnGZS2r4jfZMrqixsjmeRD6iWH8ni4iJ29QK2lz5HvXsI`"
        )
        return
    
    try:
        user_id = int(parts[1].strip())
        charge_id = parts[2].strip()
        
        if not charge_id:
            await event.respond("❌ Charge ID tidak boleh kosong")
            return
        
        # Konfirmasi ke admin
        confirm_msg = await event.respond(
            f"⚠️ **Konfirmasi Refund**\n\n"
            f"User ID: `{user_id}`\n"
            f"Charge ID: `{charge_id}`\n\n"
            f"Yakin ingin refund?\n"
            f"Ketik **YA** untuk konfirmasi, atau **TIDAK** untuk batal."
        )
        
        # Simpan data sementara
        event.client.refund_data = {
            'user_id': user_id,
            'charge_id': charge_id,
            'confirm_msg_id': confirm_msg.id,
            'chat_id': event.chat_id
        }
        
    except ValueError:
        await event.respond("❌ User ID harus berupa angka")
    except Exception as e:
        await event.respond(f"❌ Error: {str(e)}")

@bot.on(events.NewMessage)
async def handle_refund_confirmation(event):
    """Menangani konfirmasi refund dari admin"""
    if not hasattr(event.client, 'refund_data'):
        return
    
    refund_data = event.client.refund_data
    user_id = refund_data['user_id']
    charge_id = refund_data['charge_id']
    
    text = event.message.text.strip().upper()
    
    if text == 'YA':
        processing_msg = await event.respond("⏳ **Memproses refund...**")
        
        try:
            # Proses refund via API
            result = await bot(functions.payments.RefundStarsChargeRequest(
                user_id=await bot.get_input_entity(user_id),
                charge_id=charge_id
            ))
            
            await processing_msg.delete()
            
            # Hapus pesan konfirmasi
            try:
                await bot.delete_messages(
                    refund_data['chat_id'],
                    [refund_data['confirm_msg_id']]
                )
            except:
                pass
            
            # Update status di database
            db = SessionLocal()
            try:
                transaction = db.query(Transaction).filter(Transaction.charge_id == charge_id).first()
                if transaction:
                    transaction.status = 'refunded'
                    transaction.refunded_at = get_wib_time()
                    db.commit()
            finally:
                db.close()
            
            await event.respond(
                f"✅ **Refund Berhasil!**\n\n"
                f"User ID: `{user_id}`\n"
                f"Charge ID: `{charge_id}`\n\n"
                f"Stars telah dikembalikan ke user."
            )
            
            # Notifikasi user
            try:
                await bot.send_message(
                    user_id,
                    f"🔄 **Deposit Dikembalikan (Refund)**\n\n"
                    f"ID Transaksi: `{charge_id}`\n\n"
                    f"Stars telah dikembalikan ke akun Anda."
                )
            except:
                pass
            
            logger.info(f"Refund processed: {charge_id} for user {user_id}")
            
        except Exception as e:
            await processing_msg.delete()
            error_msg = str(e)
            
            if "CHARGE_NOT_FOUND" in error_msg:
                feedback = "❌ Charge ID tidak ditemukan atau tidak valid"
            elif "CHARGE_ALREADY_REFUNDED" in error_msg:
                feedback = "❌ Transaksi ini sudah direfund sebelumnya"
            else:
                feedback = f"❌ Gagal refund: {error_msg}"
            
            await event.respond(feedback)
            logger.error(f"Refund error for {charge_id}: {e}")
        
        delattr(event.client, 'refund_data')
        
    elif text == 'TIDAK':
        # Batal refund
        try:
            await bot.delete_messages(
                refund_data['chat_id'],
                [refund_data['confirm_msg_id']]
            )
        except:
            pass
        
        await event.respond("❌ Refund dibatalkan.")
        delattr(event.client, 'refund_data')

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    logger.info("="*50)
    logger.info("DEPOSIT BOT TELEGRAM STARS DIMULAI")
    logger.info("="*50)
    logger.info(f"WEBHOOK URL: {WEBHOOK_URL}")
    logger.info("="*50)
    
    await bot.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot dimatikan...")
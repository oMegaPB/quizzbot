import datetime
import asyncio

import aiogram
from aiogram.fsm.storage.memory import MemoryStorage

from handlers import router, bot, _log

async def main():
    storage = MemoryStorage()
    dp = aiogram.Dispatcher(storage=storage)
    dp.include_router(router=router)
    await bot.delete_webhook(drop_pending_updates=True)
    now = datetime.datetime.now().isoformat()
    _log.debug(f"Pending updates dropped. bot started. {now}")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())

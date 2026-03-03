"""APScheduler-based scheduler for executing time strategies."""

import uuid
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.schedule import Schedule
from app.models.device import Device
from app.models.log import OperationLog
from app.ws.manager import ws_manager

logger = logging.getLogger("app.scheduler")

# Use Asia/Shanghai timezone for China
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


async def execute_schedule(schedule_id: int):
    """Execute a scheduled action (lock/unlock/shutdown)."""
    logger.info(f"⏰ 定时任务触发: schedule_id={schedule_id}, 时间={datetime.now()}")
    db: Session = SessionLocal()
    try:
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            logger.warning(f"定时任务 {schedule_id} 不存在，跳过")
            return
        if not schedule.is_active:
            logger.warning(f"定时任务 {schedule_id} ({schedule.name}) 已禁用，跳过")
            return

        logger.info(f"📋 执行策略: {schedule.name}, 动作: {schedule.action}")

        # Get target devices
        if schedule.target_group_id:
            devices = db.query(Device).filter(Device.group_id == schedule.target_group_id).all()
        else:
            devices = db.query(Device).all()

        if not devices:
            logger.warning(f"策略 {schedule.name} 没有匹配的设备")
            return

        success_count = 0
        fail_count = 0
        for device in devices:
            task_id = uuid.uuid4().hex
            command = {
                "type": "command",
                "action": schedule.action,
                "task_id": task_id,
                "params": {},
            }
            try:
                success = await ws_manager.send_command_to_device(device.id, command)
            except Exception as e:
                logger.error(f"发送指令到设备 {device.id} ({device.name}) 失败: {e}")
                success = False

            if success:
                success_count += 1
            else:
                fail_count += 1

            log = OperationLog(
                device_id=device.id,
                action=schedule.action,
                detail=f"定时策略执行: {schedule.name}",
                result="success" if success else "failed",
            )
            db.add(log)

        db.commit()
        logger.info(f"✅ 策略 {schedule.name} 执行完毕: 成功={success_count}, 失败={fail_count}")

    except Exception as e:
        logger.error(f"❌ 定时任务执行异常 (schedule_id={schedule_id}): {e}", exc_info=True)
    finally:
        db.close()


def _weekdays_to_cron(weekdays_str: str) -> str:
    """Convert '1,2,3,4,5' weekday format to cron format.

    Input: 1=Monday ... 7=Sunday
    APScheduler day_of_week: 0=Monday ... 6=Sunday
    """
    days = [str(int(d) - 1) for d in weekdays_str.split(",")]
    return ",".join(days)


def load_schedules():
    """Load all active schedules from the database and add them to the scheduler."""
    db: Session = SessionLocal()
    try:
        # Remove existing schedule jobs
        for job in scheduler.get_jobs():
            if job.id.startswith("schedule_"):
                job.remove()

        schedules = db.query(Schedule).filter(Schedule.is_active == True).all()
        logger.info(f"📅 加载 {len(schedules)} 个活跃的定时策略")

        for s in schedules:
            hour = s.time.hour
            minute = s.time.minute
            day_of_week = _weekdays_to_cron(s.weekdays)

            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                day_of_week=day_of_week,
                timezone="Asia/Shanghai",
            )
            scheduler.add_job(
                execute_schedule,
                trigger=trigger,
                id=f"schedule_{s.id}",
                args=[s.id],
                replace_existing=True,
                misfire_grace_time=300,
            )
            # Calculate and log next fire time
            next_fire = trigger.get_next_fire_time(None, datetime.now())
            logger.info(
                f"  → 策略 [{s.name}] 动作={s.action} "
                f"时间={hour:02d}:{minute:02d} 星期={s.weekdays} "
                f"下次触发={next_fire}"
            )
    finally:
        db.close()


def list_jobs():
    """Return a list of all scheduled jobs for diagnostics."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return jobs


def start_scheduler():
    """Start the APScheduler and load schedules."""
    load_schedules()
    if not scheduler.running:
        scheduler.start()
        logger.info("🚀 定时调度器已启动")

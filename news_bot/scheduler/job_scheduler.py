"""
Job scheduler using APScheduler for automated news parsing.
"""
import asyncio
from datetime import datetime
from typing import Callable, Optional, List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database.db_manager import DatabaseManager


class JobScheduler:
    """Scheduler for automated news parsing jobs."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.db: Optional[DatabaseManager] = None
        self.parse_callback: Optional[Callable] = None
        self.job_ids: List[str] = []
    
    def initialize(
        self,
        db_manager: DatabaseManager,
        parse_callback: Callable
    ):
        """
        Initialize scheduler with dependencies.
        
        Args:
            db_manager: Database manager instance
            parse_callback: Async function to call when scheduled job runs
        """
        self.db = db_manager
        self.parse_callback = parse_callback
    
    async def start(self):
        """Start the scheduler and load existing schedules from database."""
        if not self.db:
            raise RuntimeError("Scheduler not initialized. Call initialize() first.")
        
        # Load schedules from database
        await self.load_schedules_from_db()
        
        # Start scheduler
        self.scheduler.start()
        print("Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown(wait=False)
        print("Scheduler stopped")
    
    async def load_schedules_from_db(self):
        """Load all active schedules from database and register them."""
        if not self.db:
            return
        
        schedules = await self.db.get_schedules(active_only=True)
        
        for schedule in schedules:
            self.add_job(
                day_of_week=schedule['day_of_week'],
                hour=schedule['hour'],
                minute=schedule['minute'],
                job_id=f"schedule_{schedule['id']}"
            )
    
    def add_job(
        self,
        day_of_week: int,
        hour: int,
        minute: int,
        job_id: Optional[str] = None
    ) -> bool:
        """
        Add a new scheduled job.
        
        Args:
            day_of_week: 0=Monday, 6=Sunday
            hour: Hour (0-23)
            minute: Minute (0-59)
            job_id: Optional custom job ID
            
        Returns:
            True if job added successfully
        """
        try:
            # Convert day_of_week to cron format (mon=0, sun=6)
            day_str = str(day_of_week)
            
            trigger = CronTrigger(
                day_of_week=day_str,
                hour=hour,
                minute=minute,
                timezone='Europe/Moscow'  # Adjust timezone as needed
            )
            
            job = self.scheduler.add_job(
                self._run_parse_job,
                trigger=trigger,
                id=job_id,
                name=f"News parse job (Mon={day_of_week} {hour:02d}:{minute:02d})"
            )
            
            if job_id:
                self.job_ids.append(job_id)
            
            print(f"Scheduled job added: {job.id} - {day_of_week} {hour:02d}:{minute:02d}")
            return True
            
        except Exception as e:
            print(f"Error adding scheduled job: {str(e)}")
            return False
    
    def remove_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job.
        
        Args:
            job_id: ID of job to remove
            
        Returns:
            True if job removed successfully
        """
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.job_ids:
                self.job_ids.remove(job_id)
            print(f"Job removed: {job_id}")
            return True
        except Exception as e:
            print(f"Error removing job: {str(e)}")
            return False
    
    async def _run_parse_job(self):
        """Internal method to run the parse callback."""
        if self.parse_callback:
            try:
                print(f"Running scheduled parse job at {datetime.now()}")
                if asyncio.iscoroutinefunction(self.parse_callback):
                    await self.parse_callback()
                else:
                    self.parse_callback()
            except Exception as e:
                print(f"Error in scheduled parse job: {str(e)}")
    
    def get_all_jobs(self) -> List[Dict]:
        """
        Get list of all scheduled jobs.
        
        Returns:
            List of job information dictionaries
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs
    
    def test_schedule_time(
        self,
        day_of_week: int,
        hour: int,
        minute: int
    ) -> datetime:
        """
        Test when a schedule would next run.
        
        Args:
            day_of_week: 0=Monday, 6=Sunday
            hour: Hour (0-23)
            minute: Minute (0-59)
            
        Returns:
            Next run datetime
        """
        trigger = CronTrigger(
            day_of_week=str(day_of_week),
            hour=hour,
            minute=minute,
            timezone='Europe/Moscow'
        )
        
        # Get next run time
        now = datetime.now()
        next_run = trigger.get_next_fire_time(None, now)
        
        return next_run


# Example usage
if __name__ == '__main__':
    async def mock_parse():
        print("Parse job executed!")
    
    async def main():
        db = DatabaseManager()
        await db.connect()
        
        scheduler = JobScheduler()
        scheduler.initialize(db, mock_parse)
        
        # Add test schedule (every Monday at 9:00 AM)
        scheduler.add_job(day_of_week=0, hour=9, minute=0, job_id="test_job")
        
        # Show all jobs
        jobs = scheduler.get_all_jobs()
        print("Scheduled jobs:", jobs)
        
        # Test next run time
        next_run = scheduler.test_schedule_time(0, 9, 0)
        print(f"Next run: {next_run}")
        
        # Keep running for demonstration
        await scheduler.start()
        
        try:
            # Wait indefinitely
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            scheduler.stop()
        
        await db.disconnect()
    
    asyncio.run(main())

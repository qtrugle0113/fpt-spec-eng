"""T128: business counts, timezone windows and historical schedule truth."""
from datetime import datetime,timezone
import unittest


class DashboardMetricsTests(unittest.TestCase):
    def test_success_rate_excludes_unfinished_and_unknown_states(self):
        from aat_api.services.dashboard import counts
        result=counts([{'state':state} for state in ('success','failed','running','queued','cancelled')])
        self.assertEqual(result,dict(total=5,successful=1,failed=1,running=1,queued=1,other=1,success_rate=50.0))
        self.assertIsNone(counts([])['success_rate'])

    def test_inclusive_dates_respect_dst_not_fixed_24_hour_days(self):
        from aat_api.services.dashboard import date_window
        for day,hours in [('2026-03-08',23),('2026-11-01',25)]:
            start,end=date_window(day,day,'America/New_York')
            self.assertEqual((end-start).total_seconds(),hours*3600)

    def test_run_time_uses_start_then_queue_never_logical_date(self):
        from aat_api.services.dashboard import run_time
        self.assertIsNone(run_time({'logical_date':'2026-01-01T00:00:00Z'}))
        expected=datetime(2026,1,2,tzinfo=timezone.utc)
        self.assertEqual(run_time({'queued_at':'2026-01-02T00:00:00Z','logical_date':'2025-01-01T00:00:00Z'}),expected)
        self.assertEqual(run_time({'start_date':'2026-01-02T00:00:00Z','queued_at':'2026-01-01T00:00:00Z'}),expected)

    def test_schedule_categories_do_not_guess_historical_config(self):
        from aat_api.services.schedule_statistics import group
        expected={'Manual':'Manual','0 * * * *':'Hourly','0 0 * * *':'Daily','0 0 * * 0':'Weekly','0 0 1 * *':'Monthly','7 13 * * 2':'Custom',None:'Unknown'}
        for schedule,value in expected.items():self.assertEqual(group(schedule),value)

"""Classify known schedules only; missing historical snapshots stay Unknown."""
from aat_etl.contracts.config import validate_cron

GROUPS=('Hourly','Daily','Weekly','Monthly','Custom','Manual','Unknown')


def group(schedule):
    if schedule in ('Manual','None'):return 'Manual'
    if not isinstance(schedule,str):return 'Unknown'
    aliases={'@hourly':'0 * * * *','@daily':'0 0 * * *','@weekly':'0 0 * * 0','@monthly':'0 0 1 * *'}
    schedule=aliases.get(schedule,schedule)
    presets={'0 * * * *':'Hourly','0 0 * * *':'Daily','0 0 * * 0':'Weekly','0 0 1 * *':'Monthly'}
    if schedule in presets:return presets[schedule]
    try:validate_cron(schedule)
    except ValueError:return 'Unknown'
    return 'Custom'

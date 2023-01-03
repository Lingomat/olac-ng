from datetime import datetime, timezone

def secondsToTimeString(sec) -> str:
   sec = sec % (24 * 3600)
   hour = sec // 3600
   sec %= 3600
   min = sec // 60
   sec %= 60
   return "%02d:%02d:%02d" % (hour, min, sec) 

def XMLDateToDatetime(dateobject) -> datetime | None:
    if type(dateobject) is str:
        datestring = dateobject
    elif (type(dateobject) is dict) and ('#text' in dateobject):
        datestring = dateobject['#text']
    else:
        return None
    try:
        if 'T' in datestring:
            # screw your TZ info, it's supposed to be UTC
            return datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        else:
            return datetime.strptime(datestring, "%Y-%m-%d")
    except ValueError:
        return None

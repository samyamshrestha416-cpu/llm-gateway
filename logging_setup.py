import	json
import	logging
import	sys
class	JsonFormatter(logging.Formatter):
    def	format(self,	record):
        data	=	{
            "time":	self.formatTime(record,	"%Y-%m-%dT%H:%M:%S"),
            "level":	record.levelname,
            "logger":	record.name,
            "message":	record.getMessage(),
        }
        extra	=	getattr(record,	"extra_data",	None)
        if	extra:
            data.update(extra)
        if	record.exc_info:
            data["exception"]	=	self.formatException(record.exc_info)
        return	json.dumps(data)
def	setup_logging():
    handler	=	logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root	=	logging.getLogger()
    root.handlers	=	[handler]
    root.setLevel(logging.INFO)
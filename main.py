from fastapi import FastAPI , Request
import time 
from app.config import settings
from app.llm import generate
from app.schemas import ChatRequest, ChatResponse , Usage

from fastapi.exceptions	import	RequestValidationError
from fastapi.responses	import	JSONResponse
from google.genai	import	errors
import	logging
import	uuid
from	app.logging_setup	import	setup_logging

setup_logging()
log	=	logging.getLogger("gateway")

app = FastAPI(title="LLM Gateway")

@app.middleware("http")
async	def	log_requests(request:	Request,	call_next):
    request_id	=	uuid.uuid4().hex[:8]
    request.state.request_id	=	request_id
    start	=	time.perf_counter()
    response	=	await	call_next(request)
    ms	=	int((time.perf_counter()	-	start)	*	1000)
    response.headers["X-Request-ID"]	=	request_id
    log.info("request",	extra={"extra_data":	{
        "request_id":	request_id,
        "method":	request.method,
        "path":	request.url.path,
        "status":	response.status_code,
        "duration_ms":	ms,
    }})
    return	response

@app.get("/health")
async def health():
    return {"status": "ok"}

#error details
def error_response(request , status, kind , message , **extra):
    body = {
        "error":{
            "type":kind,
            "message":message,
            "request_id": getattr(request.state , "request_id", "unknown"),
            **extra,

        }
    }
    return JSONResponse(status_code=status , content =body)

@app.exception_handler(RequestValidationError)
async def validation_handler(request :Request , exc :RequestValidationError):
    details = [
        {"field":	".".join(str(p)	for	p	in	e["loc"]),	"problem":	e["msg"]}
		for	e	in	exc.errors()
    ]
    return error_response(request,	422,	"validation_error",	"The request is not	valid.",	details=details)

@app.exception_handler(errors.APIError)
async	def	provider_error_handler(request:	Request,	exc:	errors.APIError):
    status	=	429	if	exc.code	==	429	else	502
    return	error_response(request,	status,	"provider_error","The AI provider returned an error. Please	try	again shortly.")

@app.exception_handler(Exception)
async	def	unexpected_handler(request:	Request,	exc:	Exception):
    name	=	type(exc).__name__
    if	"Connect"	in	name	or	"Timeout"	in	name:
        return	error_response(request,	503,	"provider_unreachable","Cannot	reach	the	AI	provider	right	now.")
    return	error_response(request,	500,	"internal_error",	"Something	went	wrong	on	our	side.")

@app.post("/chat" , response_model=ChatResponse)
async def chat(req : ChatRequest ,request:Request):
    start =time.perf_counter()
    reply , t_in , t_out = await generate(req.messages , req.system , req.temperature)
    ms = int((time.perf_counter() - start) * 1000)
    log.info("chat_completed",	extra={"extra_data":	{
        "request_id":request.state.request_id,
        "model":	settings.default_model,
        "input_tokens":	t_in,
        "output_tokens":	t_out,
        "latency_ms":	ms,
    }})
    return ChatResponse(
        reply  = reply,
        model = settings.default_model,
        usage = Usage(input_tokens = t_in , output_tokens = t_out , total_tokens = t_in + t_out),
        latency_ms =ms,
    )
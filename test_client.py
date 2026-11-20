import asyncio
import json
import time

import httpx

BASE = "http://127.0.0.1:8000"
BODY = {"messages":	[{"role":	"user",	"text":	"Explain	what	an	API	is	in	one	sentence."}]}

def	test_health():
	r	=	httpx.get(f"{BASE}/health")
	print("health:",	r.status_code,	r.json())

def	test_chat():
    r	=	httpx.post(f"{BASE}/chat",	json=BODY,	timeout=60)
    print("chat:",	r.status_code)
    print(json.dumps(r.json(),	indent=2))

def	test_validation():
    r	=	httpx.post(f"{BASE}/chat",	json={"messages":	[]})
    print("validation:",	r.status_code,	r.json())

def	test_stream():
    start =	time.perf_counter()
    first =	None
    event =	"message"
    with httpx.stream("POST", f"{BASE}/chat/stream", json=BODY,	timeout=60)	as r:
        for	line in	r.iter_lines():
            if line.startswith("event:"):
                event =	line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
                if event == "message":
                    if first is None:
                        first =	time.perf_counter()	- start
                    print(data["text"],	end="",	flush=True)
                else:
                    print(f"\n[{event}]	{data}")
                    event = "message"
    first_str = f"{first:.2f}s" if first is not None else "never"
    total_str = f"{time.perf_counter() - start:.2f}s"
    print(f"\nfirst piece after {first_str}, total {total_str}")

async def test_concurrent(n=5):
	async	with	httpx.AsyncClient(timeout=120)	as	c:
		start	=	time.perf_counter()
		results	=	await	asyncio.gather(*[c.post(f"{BASE}/chat",	json=BODY)	for	_	in	range(n)])
	print(f"{n}	requests	in	{time.perf_counter()	-	start:.2f}s:",	[r.status_code	for	r	in	results])
if	__name__	==	"__main__":
    test_health()
    test_chat()
    test_validation()
    test_stream()
    asyncio.run(test_concurrent())

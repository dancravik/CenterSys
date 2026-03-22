from api_assistant import *
from fastapi import FastAPI
from analytics import get_sentiment_distribution, get_top_entities_overall, get_aspect_stats, get_reviews_filtered, get_top_entities_combined, get_resonance_reviews, get_mixed_reviews

# Страницы.
@app.get("/")
@app.get("/1.html")
async def page_overview():
    return page("1.html")

@app.get("/2.html")
async def page_aspects():
    return page("2.html")

@app.get("/3.html")
async def page_reviews():
    return page("3.html")

@app.get("/4.html")
async def page_reports():
    return page("4.html")

# Эндпоинты для страниц.
@app.get("/api/aspects")
async def api_aspects():
    return get_aspect_stats

@app.get("/api/sentiment")
async def api_sentiment():
    return get_sentiment_distribution()

@app.get("/api/top5")
async def api_top5():
    return get_top_entities_overall()
#-----------------------

@app.get("/api/top-entities-combined")
async def top_entities_combined(aspect: str):
    return get_top_entities_combined(aspect)

@app.get("/api/resonance")
async def resonance(aspect: str):
    return get_resonance_reviews(aspect)

@app.get("/api/mixed")
async def mixed(aspect: str):
    return get_mixed_reviews(aspect)

#----------------------

@app.get("/api/reviews")
async def reviews_filtered(
    search: str | None = None,
    sentiment: str | None = None,
    aspect: str | None = None,
    limit: int = 20
):
    return get_reviews_filtered(search, sentiment, aspect, limit)



if __name__ == "__main__":
    sock, PORT = reserve_socket()
    console.print(f"[green]INFO[/]:     Локальная ссылка: [bright_white]http://127.0.0.1:{PORT}[/]")
    console.print(f"[green]INFO[/]:     Wi-Fi ссылка: [bright_white]http://{get_local_ip()}:{PORT}[/]")
    uvicorn.Server(uvicorn.Config(app, log_level = "info")).run(sockets = [sock])

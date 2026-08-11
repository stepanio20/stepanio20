from . import admin, auctions, market, seller, start, subscribe, watchlist

ROUTERS = [start.router, watchlist.router, auctions.router, market.router,
           subscribe.router, seller.router, admin.router]

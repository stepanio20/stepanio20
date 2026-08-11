from . import admin, auctions, seller, start, subscribe, watchlist

ROUTERS = [start.router, watchlist.router, auctions.router,
           subscribe.router, seller.router, admin.router]

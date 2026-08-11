from . import (admin, auctions, fallback, market, nav, seller, start,
               subscribe, watchlist)

# Order matters:
# - subscribe first so successful_payment is never swallowed by an FSM step
# - nav next: reply-keyboard buttons are a universal escape hatch
# - fallback last: free-text search + stale-callback catch-all
ROUTERS = [subscribe.router, nav.router, start.router, watchlist.router,
           auctions.router, market.router, seller.router, admin.router,
           fallback.router]

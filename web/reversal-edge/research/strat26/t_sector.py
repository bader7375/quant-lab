from ideas import *
Sx = pd.read_pickle("sectors.pkl"); G, SI, LOO, beta, corr = Sx["G"], Sx["SI"], Sx["LOO"], Sx["beta"], Sx["corr"]
r = np.log(C).diff().clip(-.25, .25)
b1 = beta.shift(1).clip(0, 2); res = r - b1 * LOO                       # residual = actual - beta x sector (beta known the day before)
res10 = res.rolling(10, min_periods=8).sum(); rsd = res.rolling(120, min_periods=80).std(); rz = res10 / (rsd * np.sqrt(10))
strong = corr.shift(1) >= .4
secI = np.exp(LOO.fillna(0).cumsum()); sec_hi = secI >= secI.rolling(55, min_periods=50).max()          # stock's own sector (leave-one-out) at a 55-day high
s20, k20 = r.rolling(20, min_periods=16).sum(), LOO.rolling(20, min_periods=16).sum()
F = (PCT >= .5) & MKT
tests = {
 "S1  residual z <= -2 (lagging its beta x sector), hold 10": ((rz <= -2), 10),
 "S1b residual z <= -2 & corr >= 0.4, hold 10": ((rz <= -2) & strong, 10),
 "S1c residual z <= -2 & corr >= 0.4, hold 20": ((rz <= -2) & strong, 20),
 "S2  sector at 55d high, stock lags sector 20d by 5%+, beta>=.7 corr>=.4, hold 20": (sec_hi & (s20 < k20 - .05) & (beta.shift(1) >= .7) & strong, 20),
 "S3  sector +2% today, stock < half of it, corr>=.4, hold 5": ((LOO >= .02) & (r < .5 * LOO) & strong, 5),
 "S3b sector +2% today, stock < half of it, corr>=.4, hold 10": ((LOO >= .02) & (r < .5 * LOO) & strong, 10),
}
for nm, (sg, h) in tests.items():
    rep(nm, trades(sg, None, None, h)); rep("     + ML>=50% & market model positive", trades(sg & F, None, None, h))

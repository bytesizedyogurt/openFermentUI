"""Write a FermosFitRequest of logistic series: python3 -I make_fit.py OUT.json DEPOSITION PRODUCT_UNIT SCALE
SCALE multiplies the product series (1000 with mg L-1 writes the same run in milligrams)."""
import json, math, sys
out, dep, punit, scale = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
ts = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 24]
X = lambda t: 5.0 / (1 + (5.0 - 0.1) / 0.1 * math.exp(-0.4 * t))
series = [
    {"measureId": "m-x", "label": "biomass", "unit": "g L-1", "role": "biomass",
     "points": [{"t": t, "value": round(X(t), 5), "entryId": f"x{t}", "confirmed": True} for t in ts]},
    {"measureId": "m-p", "label": "ethanol", "unit": punit, "role": "product",
     "points": [{"t": t, "value": round(4.0 * (X(t) - 0.1) * scale, 5), "entryId": f"p{t}", "confirmed": True} for t in ts]},
    {"measureId": "m-s", "label": "glucose", "unit": "g L-1", "role": "substrate",
     "points": [{"t": t, "value": round(max(0.0, 60 - 10 * (X(t) - 0.1)), 5), "entryId": f"s{t}", "confirmed": True} for t in ts]},
]
json.dump({"depositionId": dep, "series": series}, open(out, "w"))

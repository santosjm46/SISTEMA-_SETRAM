from decimal import Decimal

def fuel_efficiency(entries):
    """Consumo entre tanques llenos; acumula las cargas parciales intermedias."""
    by_bus={}; result=[]
    for entry in sorted(entries,key=lambda row:(row.bus_id,row.date,row.odometer,row.pk)):
        previous,liters=by_bus.get(entry.bus_id,(None,Decimal(0)))
        if previous is not None:liters+=entry.liters
        if entry.full_tank:
            if previous is not None and entry.odometer>previous.odometer:
                km=entry.odometer-previous.odometer
                result.append({'bus':entry.bus,'from_date':previous.date,'to_date':entry.date,'km':km,'liters':liters,'per_100':round(100*liters/km,2)})
            previous=entry;liters=Decimal(0)
        by_bus[entry.bus_id]=(previous,liters)
    return result

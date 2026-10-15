from cmms.module import Module, MANAGERS, ALL
from cmms import models as m

MODULES=[
Module('repuestos','Repuestos y existencias','Repuesto','Recursos',m.Part,('code','name','unit','minimum','unit_cost','supplier'),(('code','Código'),('name','Repuesto'),('quantity','Existencias'),('minimum','Mínimo'),('unit_cost','Costo Bs')),read=MANAGERS+('tecnico',),search=('code','name')),
Module('movimientos','Movimientos de almacén','Movimiento','Recursos',m.StockMovement,('part','kind','quantity','unit_cost','work_order','reference'),(('part','Repuesto'),('kind','Movimiento'),('quantity','Cantidad'),('work_order','OT'),('created_at','Fecha')),read=MANAGERS+('tecnico',),create=MANAGERS,edit=(),search=('reference',)),
Module('proveedores','Proveedores','Proveedor','Recursos',m.Supplier,('name','tax_id','contact','phone','email'),(('name','Proveedor'),('tax_id','NIT'),('contact','Contacto'),('phone','Teléfono')),read=MANAGERS+('tecnico',),search=('name','tax_id','contact')),
Module('compras','Órdenes de compra','Orden de compra','Recursos',m.PurchaseOrder,('supplier','part','quantity','unit_cost','expected_date','reference'),(('id','OC'),('supplier','Proveedor'),('part','Repuesto'),('quantity','Cantidad'),('total','Total Bs'),('status','Estado')),read=MANAGERS,edit=(),search=('reference',))
]
for item in MODULES:
    item.section='Inventario'
MODULES[0].fields+=('category','manufacturer','storage_location','auto_demand','application_notes')
MODULES[2].fields+=('active','lead_time_days','address','payment_terms')
MODULES.extend([
    Module('categorias_repuesto','Categorías de repuestos','Categoría','Inventario',m.PartCategory,('code','name','source_label','active'),(('code','Código'),('name','Categoría'),('source_label','Referencia'),('active','Activa')),read=MANAGERS+('tecnico',),search=('code','name','source_label')),
    Module('lineas_compra','Líneas de compra','Línea de compra','Inventario',m.PurchaseLine,('purchase','part','quantity','unit_cost'),(('purchase','OC'),('part','Repuesto'),('quantity','Pedido'),('received_quantity','Recibido')),read=MANAGERS,search=('part__name',)),
    Module('recepciones','Recepciones de compra','Recepción','Inventario',m.PurchaseReceipt,(),(('purchase','OC'),('quantity','Recibido'),('actor','Responsable'),('created_at','Fecha')),read=MANAGERS,create=(),edit=(),search=('purchase__reference',)),
    Module('demandas_compra','Demandas de reposición','Demanda','Inventario',m.PurchaseDemand,(),(('part','Repuesto'),('quantity','Solicitado'),('status','Estado'),('purchase','OC')),read=MANAGERS,create=(),edit=(),search=('part__name','part__code')),
])

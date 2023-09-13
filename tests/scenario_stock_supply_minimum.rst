=========================
Purchase Request Scenario
=========================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import (create_chart,
    ...     get_accounts)

Install stock_supply_minimum::

    >>> config = activate_modules('stock_supply_minimum')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Reload the context::

    >>> User = Model.get('res.user')
    >>> Group = Model.get('res.group')
    >>> config._context = User.get_preferences(True, config.context)

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> expense = accounts['expense']
    >>> revenue = accounts['revenue']

Create parties::

    >>> Party = Model.get('party.party')
    >>> customer = Party(name='Customer')
    >>> customer.save()
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()


Create account category::

  >>> ProductCategory = Model.get('product.category')
  >>> account_category = ProductCategory(name="Account Category")
  >>> account_category.accounting = True
  >>> account_category.account_expense = expense
  >>> account_category.account_revenue = revenue
  >>> account_category.save()


Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> ProductSupplier = Model.get('purchase.product_supplier')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'Product'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.list_price = Decimal('0')
    >>> template.purchasable = True
    >>> template.account_category = account_category
    >>> product_supplier = template.product_suppliers.new()
    >>> product_supplier.company = company
    >>> product_supplier.party = supplier

    >>> product_supplier.lead_time = datetime.timedelta(2)
    >>> product_supplier.minimum_quantity = 5
    >>> supplier_price = product_supplier.prices.new()
    >>> supplier_price.quantity = 0
    >>> supplier_price.unit_price = Decimal(14)
    >>> template.save()
    >>> product.template = template
    >>> product.cost_price = Decimal('15')
    >>> product.save()

Get stock locations::

    >>> Location = Model.get('stock.location')
    >>> warehouse_loc, = Location.find([('code', '=', 'WH')])
    >>> supplier_loc, = Location.find([('code', '=', 'SUP')])
    >>> customer_loc, = Location.find([('code', '=', 'CUS')])
    >>> output_loc, = Location.find([('code', '=', 'OUT')])
    >>> storage_loc, = Location.find([('code', '=', 'STO')])

Create a need for missing product::

    >>> ShipmentOut = Model.get('stock.shipment.out')
    >>> shipment_out = ShipmentOut()
    >>> shipment_out.planned_date = datetime.date.today()
    >>> shipment_out.effective_date = datetime.date.today()
    >>> shipment_out.customer = customer
    >>> shipment_out.warehouse = warehouse_loc
    >>> shipment_out.company = company
    >>> move = shipment_out.outgoing_moves.new()
    >>> move.product = product
    >>> move.unit = unit
    >>> move.quantity = 3
    >>> move.from_location = output_loc
    >>> move.to_location = customer_loc
    >>> move.company = company
    >>> move.unit_price = Decimal('0')
    >>> move.currency = company.currency
    >>> shipment_out.click('wait')

There is no purchase request::

    >>> PurchaseRequest = Model.get('purchase.request')
    >>> PurchaseRequest.find([])
    []

Create the purchase request::

    >>> create_pr = Wizard('stock.supply')
    >>> create_pr.execute('create_')

There is now a draft purchase request::

    >>> pr, = PurchaseRequest.find([('state', '=', 'draft')])
    >>> pr.product == product
    True
    >>> pr.party == supplier
    True
    >>> pr.quantity
    3.0
    >>> pr.minimum_quantity
    5.0

Create the purchase and check minimal quantity::

    >>> Purchase = Model.get('purchase.purchase')
    >>> create_purchase = Wizard('purchase.request.create_purchase',
    ...     [pr])
    >>> purchase, = Purchase.find()
    >>> line, = purchase.lines
    >>> line.quantity
    5.0
    >>> purchase.click('quote')

Create new need for missing product::

    >>> ShipmentOut = Model.get('stock.shipment.out')
    >>> shipment_out = ShipmentOut()
    >>> shipment_out.planned_date = datetime.date.today()
    >>> shipment_out.effective_date = datetime.date.today()
    >>> shipment_out.customer = customer
    >>> shipment_out.warehouse = warehouse_loc
    >>> shipment_out.company = company
    >>> move = shipment_out.outgoing_moves.new()
    >>> move.product = product
    >>> move.unit = unit
    >>> move.quantity = 7
    >>> move.from_location = output_loc
    >>> move.to_location = customer_loc
    >>> move.company = company
    >>> move.unit_price = Decimal('0')
    >>> move.currency = company.currency
    >>> shipment_out.click('wait')

Create the purchase request::

    >>> create_pr = Wizard('stock.supply')
    >>> create_pr.execute('create_')

There is draft purchase request::

    >>> pr, = PurchaseRequest.find([('state', '=', 'draft')])
    >>> pr.product == product
    True
    >>> pr.quantity
    7.0

Create the purchase and check minimal quantity::

    >>> Purchase = Model.get('purchase.purchase')
    >>> create_purchase = Wizard('purchase.request.create_purchase',
    ...     [pr])
    >>> purchase, = Purchase.find([
    ...     ('state', '=', 'draft'),
    ...     ])
    >>> line, = purchase.lines
    >>> line.quantity
    7.0

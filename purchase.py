# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import If, Bool, Eval

__all__ = ['ProductSupplier', 'PurchaseRequest', 'CreatePurchase',
    'PurchaseLine']


class ProductSupplier(metaclass=PoolMeta):
    __name__ = 'purchase.product_supplier'
    purchase_uom_digits = fields.Function(
        fields.Integer('Purchase UOM Digits'),
        'on_change_with_purchase_uom_digits')
    minimum_quantity = fields.Float('Minimum Quantity',
        digits=(16, Eval('purchase_uom_digits', 2)),
        depends=['purchase_uom_digits'])

    @fields.depends('product', '_parent_product.purchase_uom')
    def on_change_with_purchase_uom_digits(self, name=None):
        if self.product and self.product.purchase_uom:
            return self.product.purchase_uom.digits
        return 2


class PurchaseRequest(metaclass=PoolMeta):
    __name__ = 'purchase.request'
    minimum_quantity = fields.Function(fields.Float('Minimum Quantity',
            digits=(16, Eval('uom_digits', 2)), depends=['uom_digits']),
        'on_change_with_minimum_quantity', searcher='search_minimum_quantity')

    @fields.depends('supplier', 'product', 'uom')
    def on_change_with_minimum_quantity(self, name=None):
        Uom = Pool().get('product.uom')
        if not self.product:
            return
        for product_supplier in self.product.product_suppliers_used():
            if product_supplier.party == self.party:
                return Uom.compute_qty(self.product.purchase_uom,
                    product_supplier.minimum_quantity, self.uom)

    @classmethod
    def search_minimum_quantity(cls, name, clause):
        pool = Pool()
        Template = pool.get('product.template')
        Product = pool.get('product.product')
        ProductSupplier = pool.get('purchase.product_supplier')
        _, operator, value = clause
        Operator = fields.SQL_OPERATORS[operator]
        table = cls.__table__()
        template = Template.__table__()
        product = Product.__table__()
        product_supplier = ProductSupplier.__table__()

        query = table.join(product,
            condition=(product.id == table.product)).join(template,
                condition=(product.template == template.id)).join(
                    product_supplier, condition=(
                        (product_supplier.product == template.id) &
                        (product_supplier.party == table.party))).select(
                    table.id,
                    where=(Operator(product_supplier.minimum_quantity,
                            value)))
        return [('id', 'in', query)]


class CreatePurchase(metaclass=PoolMeta):
    __name__ = 'purchase.request.create_purchase'

    @classmethod
    def compute_purchase_line(cls, key, requests, purchase):
        line = super(CreatePurchase, cls).compute_purchase_line(key, requests,
            purchase)
        line.quantity = max([line.quantity] + [x.minimum_quantity for x in
                requests if x.minimum_quantity])
        return line


class PurchaseLine(metaclass=PoolMeta):
    __name__ = 'purchase.line'

    minimum_quantity = fields.Function(fields.Float('Minimum Quantity',
            digits=(16, Eval('unit_digits', 2)),
            states={
                'invisible': ~Bool(Eval('minimum_quantity')),
                },
            depends=['unit_digits'], help='The quantity must be greater or '
            'equal than minimum quantity'),
        'on_change_with_minimum_quantity')

    @classmethod
    def __setup__(cls):
        super(PurchaseLine, cls).__setup__()
        minimum_domain = If(
            Bool(Eval('minimum_quantity', 0)) & Bool(Eval('quantity', 0) > 0),
            ('quantity', '>=', Eval('minimum_quantity', 0)), ())
        if not 'minimum_quantity' in cls.quantity.depends:
            cls.quantity.domain.append(minimum_domain)
            cls.quantity.depends.append('minimum_quantity')

    @fields.depends('product', 'purchase', '_parent_purchase.party', 'unit')
    def on_change_with_minimum_quantity(self, name=None):
        Uom = Pool().get('product.uom')

        if not self.product or not self.purchase.party:
            return

        for product_supplier in self.product.product_suppliers_used():
            if product_supplier.party == self.purchase.party:
                minimum_quantity = product_supplier.minimum_quantity
                uom_category = self.product.purchase_uom.category
                if (minimum_quantity and self.unit and
                        self.unit in uom_category.uoms):
                    return Uom.compute_qty(self.product.purchase_uom,
                        minimum_quantity, self.unit)
                return minimum_quantity

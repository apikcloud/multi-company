# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, models
from odoo.exceptions import UserError
from odoo.sql_db import SQL


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _order_field_to_sql(self, alias, field_name, direction, nulls, query):
        # `company_id` is a related, non-stored field on `product.product`
        # (delegated to `product.template`, itself non-stored through
        # `multi.company.abstract`), so it cannot be used to build a JOIN
        # for ORDER BY. `product.product` doesn't inherit that mixin (see
        # `create`/`write` below), so replicate its skip logic here.
        fname = field_name.split(":", 1)[0].split(".", 1)[0]
        field = self._fields.get(fname)
        if fname == "company_id" and field is not None and not field.store:
            return SQL()
        return super()._order_field_to_sql(alias, field_name, direction, nulls, query)

    def _read_group_groupby(self, alias, groupby_spec, query):
        # Group on `company_ids` when asked to group on the non-stored
        # `company_id`, mirroring `multi.company.abstract` (see
        # `_order_field_to_sql` above for why this is duplicated here).
        fname = groupby_spec.split(":", 1)[0].split(".", 1)[0]
        field = self._fields.get(fname)
        if fname == "company_id" and field is not None and not field.store:
            if groupby_spec != "company_id":
                raise UserError(
                    self.env._(
                        "Grouping by %(spec)s is not supported on %(model)s "
                        "because its Company field is computed from Companies. "
                        "Group by Companies instead.",
                        spec=groupby_spec,
                        model=self._name,
                    )
                )
            return super()._read_group_groupby(alias, "company_ids", query)
        return super()._read_group_groupby(alias, groupby_spec, query)

    @api.model_create_multi
    def create(self, vals_list):
        # `company_id` and `company_ids` are related fields to
        # `product.template`, which discards `company_id` on write/create
        # when `company_ids` is also given, to prevent its `inverse` from
        # overwriting `company_ids` (see
        # `MultiCompanyAbstract._multicompany_patch_vals`). `product.product`
        # doesn't inherit that mixin, so replicate the same protection here.
        for vals in vals_list:
            self.env["product.template"]._multicompany_patch_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        self.env["product.template"]._multicompany_patch_vals(vals)
        return super().write(vals)

from odoo.addons.account.tests.account_test_users import AccountTestUsers


class TestSP(AccountTestUsers):

    def setUp(self):
        super().setUp()
        self.tax_model = self.env['account.tax']
        self.invoice_model = self.env['account.invoice']
        self.inv_line_model = self.env['account.invoice.line']
        self.fp_model = self.env['account.fiscal.position']
        self.tax22sp = self.tax_model.create({
            'name': '22% SP',
            'amount': 22,
            })
        self.tax22 = self.tax_model.create({
            'name': '22%',
            'amount': 22,
            })
        self.sp_fp = self.fp_model.create({
            'name': 'Split payment',
            'split_payment': True,
            'tax_ids': [(0, 0, {
                'tax_src_id': self.tax22.id,
                'tax_dest_id': self.tax22sp.id
            })]
            })
        self.company = self.env.ref('base.main_company')
        self.company.sp_account_id = self.env['account.account'].search([
            (
                'user_type_id', '=',
                self.env.ref('account.data_account_type_current_assets').id
            )
        ], limit=1)
        account_user_type = self.env.ref(
            'account.data_account_type_receivable')
        self.a_recv = self.account_model.sudo(self.account_manager.id).create(
            dict(
                code="cust_acc",
                name="customer account",
                user_type_id=account_user_type.id,
                reconcile=True,
            ))
        self.a_sale = self.env['account.account'].search([
            (
                'user_type_id', '=',
                self.env.ref('account.data_account_type_revenue').id)
        ], limit=1)
        self.sales_journal = self.env['account.journal'].search(
            [('type', '=', 'sale')])[0]
        # Set invoice date to recent date in the system
        # This solves problems with account_invoice_sequential_dates
        self.recent_date = self.invoice_model.search(
            [('date_invoice', '!=', False)], order='date_invoice desc',
            limit=1).date_invoice

    def test_invoice(self):
        invoice = self.invoice_model.create({
            'date_invoice': self.recent_date,
            'partner_id': self.env.ref('base.res_partner_3').id,
            'journal_id': self.sales_journal.id,
            'account_id': self.a_recv.id,
            'fiscal_position_id': self.sp_fp.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'service',
                'account_id': self.a_sale.id,
                'quantity': 1,
                'price_unit': 100,
                'invoice_line_tax_ids': [(6, 0, {
                    self.tax22sp.id
                    })]
                })]
            })
        invoice.action_invoice_open()
        invoice2 = self.invoice_model.create({
            'date_invoice': self.recent_date,
            'partner_id': self.env.ref('base.res_partner_3').id,
            'journal_id': self.sales_journal.id,
            'account_id': self.a_recv.id,
            'fiscal_position_id': self.sp_fp.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'service',
                'account_id': self.a_sale.id,
                'quantity': 1,
                'price_unit': 100,
                'invoice_line_tax_ids': [(6, 0, {
                    self.tax22.id
                    })]
                })]
            })
        invoice2.action_invoice_open()
        data = {
            'from_date': self.recent_date,
            'to_date': self.recent_date,
        }
        totals_standard_sp = self.tax22sp._compute_totals_tax(data)
        totals_standard = self.tax22._compute_totals_tax(data)

        self.assertEqual(totals_standard_sp, ('22% SP', 100.0, 22.0, 22.0, 0))
        self.assertEqual(totals_standard, ('22%', 100.0, 22.0, 22.0, 0))

        ReportVatRegistry = \
            self.env['report.l10n_it_vat_registries.report_registro_iva']
        totals_registry_sp = \
            ReportVatRegistry._compute_totals_tax(self.tax22sp, data)
        totals_registry = \
            ReportVatRegistry._compute_totals_tax(self.tax22, data)

        self.assertEqual(totals_registry_sp, ('22% SP', 100.0, 22.0, 0.0, 0))
        self.assertEqual(totals_registry, ('22%', 100.0, 22.0, 22.0, 0))

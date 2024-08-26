# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Product PDF Annotation Tool',
    'version': '17.0.0.0.0',
    'category': 'Website/Website',
    'license': 'AGPL-3',
    'sequence': 51,
    'summary': "The 'Product PDF Annotation Tool' enhances your product by enabling dynamic annotations on product PDFs. Administrators can easily add annotations with detailed descriptions to specific parts of the product PDF, allowing users to review these annotations on the website. This tool provides a seamless experience for managing and presenting product information.",

    'author': 'Quixom Technology Pvt. Ltd.',
    'maintainer': 'Quixom Technology Pvt. Ltd.',
    'website': 'https://www.quixom.com',

    'depends': ['website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_document_views.xml',
        'views/template.xml',
    ],

    'assets': {
        'web.assets_backend': [
            ('include', 'web.pdf_js_lib'),
            'qxm_product_pdf_annotation_tool/static/src/scss/product_pdf_annotation.scss',
            'qxm_product_pdf_annotation_tool/static/src/xml/product_pdf_annotation.xml',
            'qxm_product_pdf_annotation_tool/static/src/js/product_pdf_annotation.js',
            'qxm_product_pdf_annotation_tool/static/src/scss/product_pdf_preview.scss',
            'qxm_product_pdf_annotation_tool/static/src/xml/pdf_custom_preview.xml',
            'qxm_product_pdf_annotation_tool/static/src/js/pdf_custom_preview.js',
        ],
        'web.assets_frontend': [
            ('include', 'web.pdf_js_lib'),
            'qxm_product_pdf_annotation_tool/static/src/scss/product_pdf_preview.scss',
            'qxm_product_pdf_annotation_tool/static/src/xml/product_pdf_preview.xml',
            'qxm_product_pdf_annotation_tool/static/src/js/product_pdf_preview.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'images': ['static/description/banner.png'],
    'price': 99.00,
    'currency': 'USD',
}

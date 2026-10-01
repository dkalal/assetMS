from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0001_initial'),
        ('tenancy', '0012_alter_approvalrequest_request_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='externalcustomerreference',
            name='branch',
            field=models.ForeignKey(
                blank=True,
                help_text='Branch responsible for this customer.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='customers',
                to='tenancy.branch',
            ),
        ),
        migrations.AddIndex(
            model_name='externalcustomerreference',
            index=models.Index(fields=['company', 'branch'], name='extcust_company_branch'),
        ),
        migrations.CreateModel(
            name='CustomerNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='customer_notes',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('company', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='customer_notes',
                    to='tenancy.company',
                )),
                ('customer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notes',
                    to='integrations.externalcustomerreference',
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddIndex(
            model_name='customernote',
            index=models.Index(fields=['customer', 'created_at'], name='custnote_customer_created'),
        ),
    ]

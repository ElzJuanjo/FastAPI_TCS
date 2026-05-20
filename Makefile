APP_ROOT=/home/eventos
BACKEND=$(APP_ROOT)/FastAPI_TCS
VENV=$(BACKEND)/venv

.PHONY: env backend gunicorn deploy

env:
	@echo "Creando $(BACKEND)/.env desde variables del sistema..."
	@echo "SUPPORT_KEY=$$SUPPORT_KEY" > $(BACKEND)/.env
	@echo "SEAT_RESERVATION_TTL_MINUTES=$$SEAT_RESERVATION_TTL_MINUTES" >> $(BACKEND)/.env

	@echo "CORS_ORIGINS=$$CORS_ORIGINS" >> $(BACKEND)/.env

	@echo "WOMPI_API_URL=$$WOMPI_API_URL" >> $(BACKEND)/.env
	@echo "WOMPI_PUBLIC_KEY=$$WOMPI_PUBLIC_KEY" >> $(BACKEND)/.env
	@echo "WOMPI_PRIVATE_KEY=$$WOMPI_PRIVATE_KEY" >> $(BACKEND)/.env
	@echo "WOMPI_SECRET_EVENT=$$WOMPI_SECRET_EVENT" >> $(BACKEND)/.env
	@echo "WOMPI_SECRET_INTEGRITY=$$WOMPI_SECRET_INTEGRITY" >> $(BACKEND)/.env

	@echo "PLACETOPAY_URL=$$PLACETOPAY_URL" >> $(BACKEND)/.env
	@echo "PLACETOPAY_LOGIN=$$PLACETOPAY_LOGIN" >> $(BACKEND)/.env
	@echo "PLACETOPAY_TRANKEY=$$PLACETOPAY_TRANKEY" >> $(BACKEND)/.env
	@echo "PLACETOPAY_RETURN_URL=$$PLACETOPAY_RETURN_URL" >> $(BACKEND)/.env

	@echo "MSSQL_DB=$$MSSQL_DB" >> $(BACKEND)/.env
	@echo "MSSQL_STORAGE=$$MSSQL_STORAGE" >> $(BACKEND)/.env
	@echo "MSSQL_HOST=$$MSSQL_HOST" >> $(BACKEND)/.env
	@echo "MSSQL_PORT=$$MSSQL_PORT" >> $(BACKEND)/.env
	@echo "MSSQL_USER=$$MSSQL_USER" >> $(BACKEND)/.env
	@echo "MSSQL_PASSWORD=$$MSSQL_PASSWORD" >> $(BACKEND)/.env
	@echo "MSSQL_DRIVER=$$MSSQL_DRIVER" >> $(BACKEND)/.env

	@echo "SIESA_WSDL_URL=$$SIESA_WSDL_URL" >> $(BACKEND)/.env
	@echo "SIESA_F_CIA=$$SIESA_F_CIA" >> $(BACKEND)/.env
	@echo "SIESA_ID_SUCURSAL=$$SIESA_ID_SUCURSAL" >> $(BACKEND)/.env

	@echo "MAIL_SERVER=$$MAIL_SERVER" >> $(BACKEND)/.env
	@echo "MAIL_PORT=$$MAIL_PORT" >> $(BACKEND)/.env
	@echo "MAIL_USE_TLS=$$MAIL_USE_TLS" >> $(BACKEND)/.env
	@echo "MAIL_USE_SSL=$$MAIL_USE_SSL" >> $(BACKEND)/.env

	@echo "MAIL_USERNAME_ATTENDEES=$$MAIL_USERNAME_ATTENDEES" >> $(BACKEND)/.env
	@echo "MAIL_PASSWORD_ATTENDEES=$$MAIL_PASSWORD_ATTENDEES" >> $(BACKEND)/.env
	@echo "COMPANY_LOGO_URL_ATTENDEES=$$COMPANY_LOGO_URL_ATTENDEES" >> $(BACKEND)/.env
	@echo "COMPANY_LOGO_FILE_ATTENDEES=$$COMPANY_LOGO_FILE_ATTENDEES" >> $(BACKEND)/.env

	@echo "MAIL_USERNAME_TICKETS=$$MAIL_USERNAME_TICKETS" >> $(BACKEND)/.env
	@echo "MAIL_PASSWORD_TICKETS=$$MAIL_PASSWORD_TICKETS" >> $(BACKEND)/.env
	@echo "COMPANY_LOGO_URL_TICKETS=$$COMPANY_LOGO_URL_TICKETS" >> $(BACKEND)/.env
	@echo "COMPANY_LOGO_FILE_TICKETS=$$COMPANY_LOGO_FILE_TICKETS" >> $(BACKEND)/.env

	@echo "MAIL_USERNAME_CAMP=$$MAIL_USERNAME_CAMP" >> $(BACKEND)/.env
	@echo "MAIL_PASSWORD_CAMP=$$MAIL_PASSWORD_CAMP" >> $(BACKEND)/.env
	@echo "COMPANY_LOGO_URL_CAMP=$$COMPANY_LOGO_URL_CAMP" >> $(BACKEND)/.env
	@echo "COMPANY_LOGO_FILE_CAMP=$$COMPANY_LOGO_FILE_CAMP" >> $(BACKEND)/.env
	@echo "CAMP_DAY_PRICE=$$CAMP_DAY_PRICE" >> $(BACKEND)/.env

	@echo "LOG_LEVEL=$$LOG_LEVEL" >> $(BACKEND)/.env
	@echo "Backend .env creado correctamente"

backend: env
	cd $(BACKEND) && mkdir -p logs
	cd $(BACKEND) && uv sync

gunicorn:
	-pkill gunicorn
	sudo cp $(APP_ROOT)/gunicorn.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable gunicorn
	sudo systemctl restart gunicorn

deploy: backend gunicorn
	@echo "Backend desplegado correctamente"
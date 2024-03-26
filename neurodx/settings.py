"""
Django settings for citas_neuro project.

Generated by 'django-admin startproject' using Django 4.2.7.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import os
from pathlib import Path
import datetime


BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = 'django-insecure-+749%6yh6m6u-h!ft8j&1*exs16d3$vz=i^69hjv@!%exade*!'


DEBUG = True
ALLOWED_HOSTS = ['192.168.1.178']  



# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'rest_framework.authtoken',
    'neurodx',    
    'gedocumental',
    'login',
    'citas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',  
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware', 
]


ROOT_URLCONF = 'neurodx.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'neurodx.wsgi.application'


################ DESPLIEGUE 


DATABASES = {
    'default': {
        'ENGINE': 'mysql.connector.django',
        'HOST': '192.168.1.99',
        'PORT': '3306',
        'USER': 'root',
        'PASSWORD': 'root', 
        'NAME': 'neurodx',
        'OPTIONS': {
            'autocommit': True,
            'charset': 'utf8mb3',
        },
    },
     'datosipsndx': {
        'ENGINE': 'mysql.connector.django',
        'HOST': '192.168.1.99',
        'PORT': '3306',
        'USER': 'antares',
        'PASSWORD': 'dic2401',
        'NAME': 'datosipsndx',
        'OPTIONS': {
            'autocommit': True,
            'charset': 'utf8mb3',
        },
    },
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

CORS_ALLOW_ALL_ORIGINS = True

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = '/media/'


STATICFILES_DIRS = [
    str(BASE_DIR / 'static'),
    str(BASE_DIR / 'build/static')
]

ROOT_PATH_FILES_STORAGE =  '/home/server'
MEDIA_ROOT = os.path.join(ROOT_PATH_FILES_STORAGE, 'media')
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
}
CORS_ALLOW_METHODS = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS"
]

AUTH_USER_MODEL = 'login.CustomUser'
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  
]
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
CSRF_COOKIE_SECURE = False


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

CORS_ALLOW_HEADERS = [
    'Accept',
    'Accept-Language',
    'Content-Type',
    'Authorization',  
]

JWT_EXPIRATION_DELTA = datetime.timedelta(minutes=15)

FROM nginx:alpine

# Copy nginx config
COPY nginx-admin.conf /etc/nginx/conf.d/default.conf

# Copy admin portal HTML
COPY index.html /usr/share/nginx/html/index.html

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

# ==========================================
# Stage 1: Build ứng dụng (Sử dụng Node.js)
# ==========================================
FROM node:20-alpine AS builder

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy package.json và package-lock.json (nếu có)
COPY package*.json ./

# Cài đặt dependencies
RUN npm install

# Copy toàn bộ mã nguồn vào container
COPY . .

# Build ứng dụng Vite (kết quả sẽ nằm trong thư mục /app/dist)
RUN npm run build

# ==========================================
# Stage 2: Serve ứng dụng (Sử dụng Nginx)
# ==========================================
FROM nginx:alpine

# Copy kết quả build từ stage 1 (builder) sang thư mục Nginx phục vụ web
COPY --from=builder /app/dist /usr/share/nginx/html

# (Tuỳ chọn) Nếu bạn dùng React Router hoặc Vue Router ở chế độ History HTML5
# Bạn cần thêm cấu hình Nginx để redirect mọi request về index.html.
# Tạm thời chúng ta sẽ sử dụng cấu hình mặc định của Nginx.

# Khai báo port Nginx chạy (mặc định là 80)
EXPOSE 80

# Chạy Nginx
CMD ["nginx", "-g", "daemon off;"]

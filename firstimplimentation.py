
import folium

# Center map somewhere (e.g., Chicago O'Hare Airport)
m = folium.Map(location=[41.9742, -87.9073], zoom_start=10)

# Example airplane marker
folium.Marker(
    location=[41.9742, -87.9073],
    popup="Airplane at ORD",
    tooltip="Click me!",
    icon=folium.Icon(color="blue", icon="plane", prefix="fa"),
).add_to(m)

# Save to HTML
m.save("ohare.html")
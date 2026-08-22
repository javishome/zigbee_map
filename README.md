# Zigbee Map

Custom integration cho Home Assistant, vẽ sơ đồ mạng Zigbee do
[zigbee2mqtt](https://www.zigbee2mqtt.io/) báo về. Integration xin zigbee2mqtt
một network map dạng Graphviz qua MQTT rồi render ngay trong trình duyệt ở một
panel trên sidebar — không cần dịch vụ cloud, không cần thêm thư viện Python.

Có thể theo dõi nhiều instance zigbee2mqtt cùng lúc, mỗi instance một base
topic riêng, và chuyển qua lại ngay trong panel.

## Tính năng

- Panel **Zigbee Map** trên sidebar của Home Assistant.
- Theo dõi một hoặc nhiều instance zigbee2mqtt (`zigbee2mqtt`, `zigbee2mqtt2`,
  …) với ô chọn network trên toolbar. Instance không chạy sẽ được báo trạng
  thái rõ ràng chứ không làm panel hỏng.
- Đếm thiết bị theo loại: coordinator, router (cắm điện), end device (dùng
  pin) — kèm filter bật/tắt từng loại.
- Filter theo chữ trên friendly name, địa chỉ IEEE và model: thiết bị khớp
  được làm nổi, các thiết bị lân cận mờ vừa, còn lại mờ hẳn.
- Bấm vào thiết bị để xem địa chỉ, model và link quality (LQI) tới từng thiết
  bị lân cận.
- Sáu layout engine của Graphviz (`circo`, `dot`, `fdp`, `neato`, `osage`,
  `twopi`), kéo, zoom và fit-to-view.
- Giao diện sáng/tối, tự theo trình duyệt và đổi tay được.
- Service `zigbee2mqtt_networkmap.update`, có thể giới hạn cho một network.

## Yêu cầu

- Home Assistant 2024.11 hoặc mới hơn, đã cài
  [MQTT integration](https://www.home-assistant.io/integrations/mqtt/).
- Một hoặc nhiều instance zigbee2mqtt trên cùng MQTT broker.
- Folder `<config>/www` ghi được — assets của panel được copy sang
  `<config>/www/community/zigbee2mqtt_networkmap/` lúc khởi động.

## Cài đặt

### HACS (khuyến nghị)

1. Trong HACS, thêm repo này làm custom repository loại **Integration**.
2. Cài **Zigbee Map**.
3. Restart Home Assistant.
4. Vào **Settings → Devices & services → Add integration** rồi chọn
   **Zigbee map**.

### Thủ công

1. Copy `custom_components/zigbee2mqtt_networkmap` vào folder
   `<config>/custom_components/`.
2. Restart Home Assistant.
3. Thêm integration ở **Settings → Devices & services**.

## Cấu hình

Form cài đặt hỏi danh sách **base topics** cần theo dõi — mỗi instance
zigbee2mqtt một dòng. Mỗi giá trị phải khớp `mqtt.base_topic` của instance đó:

| Instance | Base topic |
| --- | --- |
| Add-on zigbee2mqtt thứ nhất | `zigbee2mqtt` |
| Add-on thứ hai | `zigbee2mqtt2` |
| Add-on thứ ba | `zigbee2mqtt3` |

Thêm hoặc bớt topic sau này qua nút **Configure** của integration; lưu xong
integration tự nạp lại.

Khai một topic trước khi add-on tương ứng tồn tại cũng được. Không bắt buộc
phải có ai trả lời: network đó hiện là **not seen** trong panel, mọi thứ còn
lại vẫn chạy bình thường.

Chỉ hỗ trợ **một** instance của *integration*, vì assets của panel được ghi vào
một folder dùng chung. Muốn theo dõi nhiều instance zigbee2mqtt thì khai nhiều
base topic, không phải thêm integration nhiều lần.

## Sử dụng

Mở **Zigbee Map** trên sidebar.

- **Network** chọn instance zigbee2mqtt để hiển thị, kèm trạng thái ngay cạnh
  tên: `online`, `offline`, hoặc `not seen` (chưa nghe thấy gì từ nó).
- **Update** xin map mới từ instance đang chọn. Nút mũi tên kép bên cạnh xin
  toàn bộ instance đã cấu hình.
- zigbee2mqtt phải đi hết mesh nên một lần quét mất từ vài giây tới một hai
  phút; panel poll mỗi ba giây và bỏ cuộc sau hai phút, kèm thông báo nêu tên
  instance im lặng.
- Rời panel không hủy việc quét. Request nằm ở integration chứ không nằm ở
  trình duyệt, nên map vẫn về và vẫn được lưu trong lúc bạn đang ở chỗ khác.
  Mở lại panel là thấy map, và nếu việc quét vẫn đang chạy (bắt đầu chưa quá ba
  phút) thì panel nối lại việc chờ chứ không bắt quét lần nữa.
- **Device types** ở góc dưới bên trái cho biết map có bao nhiêu coordinator,
  router và end device; bấm vào một dòng để ẩn loại đó.
- **Filter devices** làm nổi thiết bị khớp và làm mờ phần còn lại.

Phím tắt: `/` vào ô filter, `1`/`2`/`3` bật tắt từng loại thiết bị, `n` sang
network tiếp theo, `r` update network đang chọn, `Shift+R` update tất cả, `+`/`-`
zoom, `f` fit to view, `Esc` xóa filter và bỏ chọn.

### Service

```yaml
# Làm mới toàn bộ instance đã cấu hình
action: zigbee2mqtt_networkmap.update
```

```yaml
# Làm mới một instance
action: zigbee2mqtt_networkmap.update
data:
  network: zigbee2mqtt2
```

`network` cũng nhận một danh sách. Base topic không tồn tại sẽ báo lỗi kèm
danh sách các topic đã cấu hình.

### Các state object

| Entity | Ý nghĩa |
| --- | --- |
| `zigbee2mqtt_networkmap.<topic>_last_update` | Thời điểm map gần nhất của network đó, một entity cho mỗi base topic |
| `zigbee2mqtt_networkmap.map_last_update` | Thời điểm của network vừa cập nhật gần nhất, kèm attribute `network` |

Entity id theo từng network dùng base topic đã slugify, ví dụ
`zigbee2mqtt_networkmap.zigbee2mqtt2_last_update`.

## Cách hoạt động

1. Lúc setup, integration copy folder `www/` của nó sang
   `<config>/www/community/zigbee2mqtt_networkmap/` và ghi file `settings.js`
   chứa hai webhook ID mới sinh cùng danh sách topic đang theo dõi.
2. Với mỗi base topic, integration subscribe
   `<topic>/bridge/response/networkmap` (nhận map) và `<topic>/bridge/state`
   (biết instance có online hay không — đọc được cả payload kiểu cũ
   `online`/`offline` lẫn kiểu mới `{"state": "online"}`).
3. Panel là một custom element nhỏ, nhúng `map.html` trong iframe.
4. **Update** gọi webhook trigger kèm network cần quét, webhook này publish
   `graphviz` lên `<topic>/bridge/request/networkmap`.
5. Kết quả được giữ trong memory và ghi ra `source.js` dưới dạng
   `networks_data`, khóa theo base topic.
6. Panel poll webhook check tới khi map về, render bằng
   [viz.js](https://github.com/mdaines/viz.js) (bản build WebAssembly của
   Graphviz) và cho kéo/zoom bằng
   [panzoom](https://github.com/anvaka/panzoom).

Webhook ID được sinh lại mỗi lần restart, nên `settings.js` luôn được nạp kèm
tham số chống cache.

## Cấu trúc repo

```
custom_components/zigbee2mqtt_networkmap/
├── __init__.py        # setup, phần MQTT, webhook, service, panel
├── config_flow.py     # config flow + options flow
├── const.py           # hằng số dùng chung
├── manifest.json
├── services.yaml
├── strings.json
├── translations/      # en, vi
└── www/               # assets được copy vào <config>/www/community/
    ├── map.html
    ├── zigbee2mqtt-map-panel.js
    ├── panzoom/
    └── viz.js/
```

## Xử lý sự cố

**Panel báo thiếu webhook ID.** Không ghi được `settings.js`. Kiểm tra folder
`<config>/www/community/zigbee2mqtt_networkmap/` có tồn tại và ghi được không,
rồi restart Home Assistant.

**Một network hiện là "not seen".** Chưa nhận được gì trên
`<topic>/bridge/state`. Hoặc instance zigbee2mqtt đó không chạy, hoặc
`mqtt.base_topic` của nó khác với giá trị khai ở đây.

**Không có phản hồi sau hai phút.** Base topic không khớp với gì trên broker.
Subscribe `<topic>/bridge/response/networkmap` bằng một MQTT client sẽ biết
zigbee2mqtt có trả lời hay không.

**Layout bị đè lên nhau.** `neato` và `fdp` đã được chèn `overlap=false` cùng
curved splines; nếu map vẫn chật thì thử `circo` hoặc `dot`.

**Vẫn thấy giao diện cũ sau khi update.** Home Assistant serve `/local` kèm
cache header dài, nên trình duyệt có thể vẫn dùng bản cũ. Reload integration
(hoặc restart Home Assistant) để `module_url` mang token mới, rồi hard reload
trình duyệt một lần bằng `Ctrl+Shift+R`.

## Ghi công

Dựa trên ý tưởng gốc
[zigbee2mqtt_networkmap](https://github.com/rgruebel/ha_zigbee2mqtt_networkmap),
được đóng gói và bảo trì bởi [javishome](https://github.com/javishome).

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.animation import Animation
import subprocess
import os
import shutil


class ButtonGrid(GridLayout):
    def __init__(self, status_label, current_file_label, **kwargs):
        super().__init__(**kwargs)
        self.cols = 3
        self.rows = 5
        self.spacing = 10
        self.padding = [10, 10, 10, 10]
        self.size_hint_y = 0.75
        self.active_process = None
        self.db_exists = os.path.exists("duzenli_data.db")
        self.status_label = status_label
        self.current_file_label = current_file_label

        self.commands = [
            ("bot_giris_grafigi.py", "Bot Giriş Grafiği"),
            ("browser_karsılastırma_tablosu.py", "Tarayıcı Karşılaştırma Tablosu"),
            ("browser_kullanim_grafigi.py", "Tarayıcı Kullanım Grafiği"),
            ("cohort_analiz_grafigi.py", "Cohort Analiz Grafiği"),
            ("girilen_sayfa_grafigi.py", "Girilen Sayfa Grafiği"),
            ("hata_veren_sayfalar_istatistigi.py", "Hata Veren Sayfa İstatistiği"),
            ("ip_konum_karsilastirma_tablosu.py", "IP Konum Karşılaştırması"),
            ("ip_world_location_haritage.py", "Dünya IP Konum Haritası"),
            ("kullanici_geri_donus_istatistigi.py", "Kullanıcı Geri Dönüş İstatistiği"),
            ("os_mobile_pc_istatistigi.py", "Mobil / PC İşletim Sistemi"),
            ("referer_istatistigi.py", "Referer İstatistiği"),
            ("saat_tarih_ip_grafik.py", "Saat-Tarih-IP Grafiği"),
            ("sayfa_sonrası_ziyaret_grafigi.py", "Sayfa Sonrası Ziyaret"),
            ("status_code_grafigi.py", "HTTP Durum Kodları"),
            ("trafik_yogunluk_grafigi.py", "Trafik Yoğunluğu Grafiği"),
        ]

        colors = [
            "#FFCDD2", "#F8BBD0", "#E1BEE7", "#D1C4E9", "#C5CAE9",
            "#BBDEFB", "#B3E5FC", "#B2EBF2", "#B2DFDB", "#C8E6C9",
            "#DCEDC8", "#F0F4C3", "#FFF9C4", "#FFE0B2", "#FFCCBC"
        ]

        for i, (filename, label) in enumerate(self.commands):
            btn = Button(
                text=label,
                background_color=self.hex_to_rgba(colors[i]),
                font_size=14,
                size_hint=(1, None),
                height=70
            )
            btn.bind(on_press=self.create_callback(filename, label))
            btn.bind(on_press=self.animate_button)
            self.add_widget(btn)

        # İşlem durumunu her saniye kontrol et
        Clock.schedule_interval(self.check_process_status, 1)

    def create_callback(self, filename, label=None):
        def callback(instance):
            self.db_exists = os.path.exists("duzenli_data.db")
            if not self.db_exists:
                self.status_label.text = "Veri dosyası bulunamadı!"
                return

            if self.active_process and self.active_process.poll() is None:
                try:
                    self.active_process.terminate()
                    self.active_process.wait(timeout=2)
                except Exception as e:
                    print(f"İşlem sonlandırılamadı: {e}")

            try:
                self.status_label.text = ""
                self.active_process = subprocess.Popen(
                    ["python", filename],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print(f"{filename} çalıştırılıyor...")
                if label:
                    self.current_file_label.text = f"Çalışan grafik: {label}"
            except Exception as e:
                self.status_label.text = f"Hata: {e}"
        return callback

    def animate_button(self, instance):
        original_width, original_height = instance.size

        def shrink(animation, widget):
            widget.size = (original_width * 0.95, original_height * 0.95)

        def restore(animation, widget):
            widget.size = (original_width, original_height)

        anim = Animation(duration=0.1)
        anim.bind(on_start=shrink)
        anim += Animation(duration=0.1)
        anim.bind(on_complete=restore)
        anim.start(instance)

    def hex_to_rgba(self, hex_color, alpha=1):
        hex_color = hex_color.lstrip('#')
        r, g, b = [int(hex_color[i:i+2], 16)/255. for i in (0, 2, 4)]
        return (r, g, b, alpha)

    def check_process_status(self, dt):
        if self.active_process:
            if self.active_process.poll() is not None:  # işlem sona ermiş
                self.active_process = None
                self.current_file_label.text = "Çalışan grafik: Yok"


class DragDropArea(BoxLayout):
    def __init__(self, button_grid, output_label, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = 0.15
        self.label = Label(text="db uzantılı dosyayı buraya sürükleyin", font_size=16, size_hint_y=None, height=40)
        self.add_widget(self.label)
        self.button_grid = button_grid
        self.output_label = output_label
        self.process = None

        Window.bind(on_dropfile=self.on_file_drop)

    def on_file_drop(self, window, file_path):
        Clock.schedule_once(lambda dt: self.handle_file_drop(file_path), 0.1)

    def handle_file_drop(self, file_path):
        file_path = file_path.decode("utf-8")
        print(f"Sürüklenen dosya: {file_path}")

        if not file_path.endswith(".db"):
            self.label.text = "Sadece .db dosyaları kabul edilir."
            return

        try:
            filename = os.path.basename(file_path)
            current_dir = os.getcwd()
            destination_path = os.path.join(current_dir, filename)

            if not os.path.exists(destination_path):
                shutil.copy(file_path, destination_path)
                print(f"Kopyalandı: {destination_path}")
            else:
                print(f"Zaten var: {destination_path}")

            self.label.text = f"{filename} yüklendi\n{filename} -> duzenli_data.db"
            self.output_label.text = "Data düzenleniyor ..."

            self.process = subprocess.Popen(
                ["python", "data_siralama.py", destination_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            Clock.schedule_interval(self.read_output, 0.5)

            self.button_grid.db_exists = True
            self.button_grid.status_label.text = ""

        except Exception as e:
            self.label.text = f"Hata: {e}"
            print(f"Hata oluştu: {e}")

    def read_output(self, dt):
        if self.process:
            output = self.process.stdout.readline()
            if output:
                self.output_label.text = output.strip()
            elif self.process.poll() is not None:
                err_output = self.process.stderr.read()
                if err_output:
                    self.output_label.text = err_output.strip()
                else:
                    self.output_label.text = "Data düzenlendi!"
                self.process = None
                return False
        return True


class GrafikUygulamasi(App):
    def build(self):
        ana_layout = BoxLayout(orientation='vertical')

        status_label = Label(text="", size_hint_y=None, height=40)
        output_label = Label(text="", size_hint_y=None, height=40, font_size=14)
        current_file_label = Label(text="Çalışan grafik: Yok", size_hint_y=None, height=40, font_size=14)

        btn_grid = ButtonGrid(status_label=status_label, current_file_label=current_file_label)
        drag_area = DragDropArea(button_grid=btn_grid, output_label=output_label)

        ana_layout.add_widget(status_label)
        ana_layout.add_widget(btn_grid)
        ana_layout.add_widget(drag_area)
        ana_layout.add_widget(current_file_label)
        ana_layout.add_widget(output_label)

        return ana_layout


if __name__ == "__main__":
    GrafikUygulamasi().run()

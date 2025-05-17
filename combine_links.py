import os
import re

def get_latest_combined_file_index(folder_path):
    max_index = 0
    pattern = re.compile(r"combined_property_links_(\d+)\.txt")
    for file in os.listdir(folder_path):
        match = pattern.match(file)
        if match:
            index = int(match.group(1))
            max_index = max(max_index, index)
    return max_index

def read_all_combined_links(folder_path):
    links = set()
    pattern = re.compile(r"combined_property_links_\d+\.txt")
    for file in os.listdir(folder_path):
        if pattern.match(file):
            file_path = os.path.join(folder_path, file)
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    links.add(line.strip())
    return links

def combine_property_links(base_folder):
    combined_folder = os.path.join(base_folder, "combined_links")
    os.makedirs(combined_folder, exist_ok=True)

    previous_links = read_all_combined_links(combined_folder)
    current_new_links = set()
    session_count = 0
    file_created = None

    for entry in os.listdir(base_folder):
        session_path = os.path.join(base_folder, entry)
        if os.path.isdir(session_path) and entry != "combined_links":
            links_file = os.path.join(session_path, "property_links.txt")
            if os.path.isfile(links_file):
                session_count += 1
                with open(links_file, "r", encoding="utf-8") as f:
                    for line in f:
                        link = line.strip()
                        if link and link not in previous_links:
                            current_new_links.add(link)

    if current_new_links:
        new_index = get_latest_combined_file_index(combined_folder) + 1
        new_combined_file = os.path.join(combined_folder, f"combined_property_links_{new_index:02}.txt")
        with open(new_combined_file, "w", encoding="utf-8") as f:
            for link in sorted(current_new_links):
                f.write(link + "\n")
        file_created = new_combined_file
        print("✅ Sesi penggabungan selesai:")
    else:
        print("ℹ️  Tidak ditemukan link baru.")

    # Ringkasan info
    print("\n📊 RINGKASAN")
    print("──────────────────────────────")
    print(f"📁 Folder sesi diproses     : {session_count}")
    print(f"🔗 Total link sebelumnya     : {len(previous_links)}")
    print(f"🆕 Link baru di sesi ini     : {len(current_new_links)}")
    print(f"📦 Total link keseluruhan    : {len(previous_links | current_new_links)}")
    if file_created:
        print(f"💾 File link baru dibuat     : {os.path.basename(file_created)}")
    else:
        print("💾 Tidak ada file baru dibuat")

if __name__ == "__main__":
    base_results_folder = os.path.join(os.getcwd(), "results")
    combine_property_links(base_results_folder)

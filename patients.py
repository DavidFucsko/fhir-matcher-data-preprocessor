import json
import os
import uuid
import random
import cProfile

from fhir.resources.address import Address
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.contactpoint import ContactPoint
from fhir.resources.fhirdate import FHIRDate
from fhir.resources.humanname import HumanName
from fhir.resources.patient import Patient

name_transformations = {
    "switch": lambda index, prefix, given,
                     family: f"COL name{index} VAL {prefix[0] if prefix else ''} {family} {given[0] if given else ''} ",
    "missing_prefix": lambda index, prefix, given, family: f"COL name{index} VAL {family} {given[0] if given else ''} ",
    "missing_given": lambda index, prefix, given, family: f"COL name{index} VAL {family} "
}


def collect_names(names, is_transform):
    result = ""
    going_to_transform = False if not is_transform else random.choice([True, False])
    for idx, name in enumerate(names):
        if isinstance(name, HumanName):
            prefix = name.prefix[0] if name.prefix else ''
            given = name.given[0] if name.given else ''
            result += f"COL name{idx} VAL {prefix} {given} {name.family} " \
                if not going_to_transform else \
                name_transformations[random.choice(list(name_transformations.keys()))](idx, prefix, given, name.family)
    return result


def collect_telecoms(telecoms):
    result = ""
    for idx, telecom in enumerate(telecoms):
        if isinstance(telecom, ContactPoint):
            result += f"COL telecom{idx} VAL {telecom.system} {telecom.value} {telecom.use} "
    return result


def collect_addresses(addresses):
    result = ""
    for idx, address in enumerate(addresses):
        if isinstance(address, Address):
            result += f"COL address{idx} VAL {address.line[0] if address.line else ''} {address.city} {address.state} {address.postalCode} {address.country}"
    return result


def collect_patient_resources(out_file, is_transform=False):
    data_folder = os.listdir("data")
    for idx, filename in enumerate(data_folder):
        f = os.path.join("data", filename)
        if os.path.isfile(f):
            with open(f, "r", encoding="utf-8") as read_file:
                data = json.load(read_file)
            bundle = Bundle(data)
            with open(f"{out_file}.txt", "a", encoding="utf-8") as of:
                patient_entries = [entry for (idx, entry) in enumerate(bundle.entry) if
                                   isinstance(entry, BundleEntry) and isinstance(entry.resource, Patient)]
                for entry in patient_entries:
                    resource = entry.resource
                    names = collect_names(resource.name, is_transform)
                    telecoms = collect_telecoms(resource.telecom)
                    addresses = collect_addresses(resource.address)
                    patient_line = f"COL id VAL {resource.id if not is_transform else str(uuid.uuid4())} " \
                                   f"{names} " \
                                   f"{telecoms} " \
                                   f"COL gender VAL {resource.gender} " \
                                   f"COL birthDate VAL {resource.birthDate.date if isinstance(resource.birthDate, FHIRDate) else ''} " \
                                   f"COL deceasedDateTime VAL {resource.deceasedDateTime.date if isinstance(resource.deceasedDateTime, FHIRDate) else ''} " \
                                   f"{addresses}" \
                                   f"COL maritalStatus VAL {resource.maritalStatus.text} "
                    print(patient_line, file=of)
                    print(f"Processing: {idx} of {len(data_folder)} {read_file.name}")


def get_specific_line(file_path, line_number):
    try:
        with open(file_path, 'r', encoding="utf-8") as file:
            lines = file.readlines()
            if 0 < line_number <= len(lines):
                return lines[line_number - 1]  # Adjust index to line number
            else:
                return "Line number out of range."
    except FileNotFoundError:
        return "File not found."


def random_except(excluded_value, start, end):
    while True:
        random_number = random.randint(start, end)
        if random_number != excluded_value:
            return random_number


def shuffle_lines(filein):
    with open(filein, "r", encoding="utf-8") as file:
        lines = file.readlines()
        random.shuffle(lines)
    with open(filein, "w", encoding="utf-8") as file:
        file.writelines(lines)


def split_dataset(out_file, file, line_count, ratio, start):
    file.seek(0)
    with open(out_file, "w", encoding="utf-8") as of:
        end = start + (line_count * ratio)
        print(f"{end} {start} {line_count}")
        for idx, line in enumerate(file):
            if start <= idx <= end:
                over_half = idx + 1 >= (start+end) / 2
                original = line.strip("\n")
                transformed = get_specific_line("patient_transformed.txt",
                                                idx + 1 if not over_half else
                                                random_except(idx + 1, 1, line_count)).strip("\n")
                print(f"{original} \t {transformed} \t {'1' if not over_half else '0'}", file=of)
            if idx + 1 >= end:
                break
    shuffle_lines(out_file)


def mix_transformed():
    with open("patient_train.txt", "r", encoding="utf-8") as file:
        line_count = sum(1 for l in file)
        split_dataset("train.txt", file, line_count, 0.8, 0)
        split_dataset("test.txt", file, line_count, 0.1, line_count*0.8)
        split_dataset("valid.txt", file, line_count, 0.1, line_count * 0.9)


def generate_training_data():
    collect_patient_resources("patient_train")
    collect_patient_resources("patient_transformed", True)
    mix_transformed()


if __name__ == '__main__':
    generate_training_data()
    # cProfile.run('generate_training_data()')

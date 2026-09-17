# Cohort Lens Context

เอกสารนี้กำหนดคำศัพท์หลักของงานศึกษาความเป็นไปได้ของ cohort เพื่อให้ผู้ใช้
นักพัฒนา และผู้ตรวจสอบใช้ความหมายเดียวกัน

## Cohort feasibility language

**Cohort**:
กลุ่มบุคคลที่ผ่านเงื่อนไขการคัดเลือกของคำถามวิจัยหนึ่งชุด
_Avoid_: patient list, sample

**Index event (T0)**:
เหตุการณ์ที่ทำให้บุคคลเข้าสู่การพิจารณา cohort และเป็นจุดอ้างอิงของเวลา
สำหรับเงื่อนไขอื่น โดยใช้วันที่ของเหตุการณ์ที่ตรงเงื่อนไขเร็วที่สุดเป็น T0
_Avoid_: start event, baseline record

**Demographic filter**:
เงื่อนไขด้านอายุหรือเพศของบุคคล ณ T0
_Avoid_: patient profile

**Inclusion criterion**:
เงื่อนไขเหตุการณ์หรือคุณสมบัติที่บุคคลต้องผ่านหลังจากมีสิทธิ์ตาม T0
_Avoid_: inclusion rule เมื่อหมายถึงผลลัพธ์ของการคัดเลือกทั้งชุด

**Exclusion criterion**:
เงื่อนไขเหตุการณ์หรือคุณสมบัติที่ทำให้บุคคลถูกนำออกจาก cohort หลังผ่านขั้นก่อนหน้า
_Avoid_: reject list

**Feasibility run**:
การประเมิน cohort configuration หนึ่งครั้งที่คืนจำนวนบุคคลในแต่ละขั้นและจำนวน
ใน final cohort
_Avoid_: patient extraction, analysis result

**Attrition**:
ลำดับจำนวนบุคคลที่เหลือหลังผ่าน T0, demographic, inclusion และ exclusion
เพื่ออธิบายว่าจำนวนลดลงในขั้นใด
_Avoid_: drop-off chart เมื่อหมายถึงผลลัพธ์ทั้งหมด

**Saved cohort**:
ชื่อและนิยาม cohort ที่บันทึกไว้เพื่อเรียกกลับมาใช้ซ้ำ
_Avoid_: saved result; การบันทึกนี้ไม่ใช่ feasibility run

## Audit language

**Audit session**:
ช่วงการใช้งานของผู้ใช้ที่ใช้รวม page views และ feasibility runs ที่เกิดขึ้นใน
session เดียวกัน
_Avoid_: login event; session log ไม่ได้หมายถึงประวัติการยืนยันตัวตนทุกเหตุการณ์

**Feasibility run record**:
บันทึกผล สเปกเงื่อนไข และ SQL preview ของ feasibility run เพื่อให้ผู้ใช้ตรวจสอบ
ย้อนหลังได้ โดยไม่ใช่ข้อมูลผู้ป่วยรายบุคคล
_Avoid_: clinical data extract

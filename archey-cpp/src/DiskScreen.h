#pragma once
#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QListWidget>
#include <QButtonGroup>
#include <QRadioButton>
#include <QSlider>
#include <QProcess>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QFrame>
#include <QScrollArea>
#include "Theme.h"
#include "InstallState.h"

class DiskScreen : public QWidget {
    Q_OBJECT
signals:
    void confirmed(QVariantMap disk, QVariantMap efi, double sizeGb, QString mode);
    void back();

public:
    explicit DiskScreen(QWidget* parent = nullptr) : QWidget(parent) {
        auto* scroll = new QScrollArea(this);
        scroll->setWidgetResizable(true);
        scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
        auto* outerLayout = new QVBoxLayout(this);
        outerLayout->setContentsMargins(0,0,0,0);
        outerLayout->addWidget(scroll);

        auto* inner = new QWidget();
        scroll->setWidget(inner);
        auto* root = new QVBoxLayout(inner);
        root->setContentsMargins(48,40,48,32);
        root->setSpacing(12);

        auto* t = new QLabel("Disk Setup"); t->setObjectName("title");
        auto* s = new QLabel("Select a disk and installation mode.");
        s->setObjectName("sub"); s->setWordWrap(true);
        root->addWidget(t); root->addWidget(s);

        // Disk list
        auto* diskLbl = new QLabel("SELECT DISK"); diskLbl->setObjectName("sec");
        root->addWidget(diskLbl);
        m_diskList = new QListWidget();
        m_diskList->setFixedHeight(140);
        root->addWidget(m_diskList);
        connect(m_diskList, &QListWidget::currentRowChanged, this, &DiskScreen::onDiskSelected);

        // Visual partition bar
        m_barLbl = new QLabel();
        m_barLbl->setFixedHeight(28);
        m_barLbl->setStyleSheet(QString("background:%1; border-radius:6px;").arg(Theme::BG3));
        root->addWidget(m_barLbl);

        // Mode selector
        auto* modeLbl = new QLabel("INSTALL MODE"); modeLbl->setObjectName("sec");
        root->addWidget(modeLbl);

        auto* modeGroup = new QButtonGroup(this);
        QStringList modeNames  = {"Wipe disk",     "Free space",    "Dual boot"};
        QStringList modeIds    = {"wipe",           "freespace",     "dualboot"};
        QStringList modeDescs  = {
            "Erase everything and do a clean install.",
            "Install alongside existing OS using free space.",
            "Shrink Windows partition and install beside it."
        };
        for (int i = 0; i < 3; ++i) {
            auto* card = new QFrame();
            card->setStyleSheet(QString("QFrame{background:%1;border:1px solid %2;border-radius:10px;padding:4px;}").arg(Theme::BG2).arg(Theme::BORDER));
            auto* cv = new QVBoxLayout(card);
            cv->setContentsMargins(12,10,12,10);
            auto* rb = new QRadioButton(modeNames[i]);
            rb->setProperty("modeId", modeIds[i]);
            modeGroup->addButton(rb, i);
            auto* desc = new QLabel(modeDescs[i]);
            desc->setObjectName("hint"); desc->setWordWrap(true);
            cv->addWidget(rb); cv->addWidget(desc);
            root->addWidget(card);
            if (i == 0) { rb->setChecked(true); m_mode = "wipe"; }
        }
        connect(modeGroup, &QButtonGroup::idToggled, this, [this, modeGroup](int id, bool checked){
            if (checked) {
                auto* rb = qobject_cast<QRadioButton*>(modeGroup->button(id));
                if (rb) m_mode = rb->property("modeId").toString();
                updateSizeSlider();
            }
        });

        // Size slider (shown for dualboot/freespace)
        m_sizeFrame = new QFrame();
        auto* sv = new QVBoxLayout(m_sizeFrame);
        sv->setContentsMargins(0,0,0,0);
        auto* sizeLblRow = new QHBoxLayout();
        auto* sizeLbl = new QLabel("ARCH SIZE"); sizeLbl->setObjectName("sec");
        m_sizeLbl = new QLabel("40 GB");
        m_sizeLbl->setStyleSheet(QString("font-size:13px; color:%1;").arg(Theme::PINK));
        sizeLblRow->addWidget(sizeLbl); sizeLblRow->addStretch(); sizeLblRow->addWidget(m_sizeLbl);
        m_sizeSlider = new QSlider(Qt::Horizontal);
        m_sizeSlider->setRange(10, 500);
        m_sizeSlider->setValue(40);
        connect(m_sizeSlider, &QSlider::valueChanged, this, [this](int v){
            m_archSizeGb = v;
            m_sizeLbl->setText(QString("%1 GB").arg(v));
        });
        sv->addLayout(sizeLblRow);
        sv->addWidget(m_sizeSlider);
        m_sizeFrame->setVisible(false);
        root->addWidget(m_sizeFrame);

        // Buttons
        auto* btnRow = new QHBoxLayout();
        m_backBtn = new QPushButton("← Back"); m_backBtn->setObjectName("secondary"); m_backBtn->setStyleSheet(Theme::secondaryBtn());
        m_confirmBtn = new QPushButton("Confirm & Continue →"); m_confirmBtn->setObjectName("primary"); m_confirmBtn->setStyleSheet(Theme::primaryBtn());
        m_confirmBtn->setEnabled(false);
        connect(m_backBtn, &QPushButton::clicked, this, &DiskScreen::back);
        connect(m_confirmBtn, &QPushButton::clicked, this, &DiskScreen::onConfirm);
        btnRow->addWidget(m_backBtn); btnRow->addStretch(); btnRow->addWidget(m_confirmBtn);
        root->addLayout(btnRow);

        loadDisks();
    }

private slots:
    void onDiskSelected(int row) {
        if (row < 0 || row >= m_disks.size()) return;
        m_selectedDisk = row;
        m_confirmBtn->setEnabled(true);
        updateBar();
    }

    void onConfirm() {
        if (m_selectedDisk < 0) return;
        QVariantMap disk = m_disks[m_selectedDisk];
        QVariantMap efi;
        // Find EFI partition on selected disk
        for (const auto& p : m_partitions[m_selectedDisk]) {
            QVariantMap pm = p.toMap();
            if (pm["parttype"].toString().contains("c12a7328", Qt::CaseInsensitive) ||
                pm["fstype"].toString() == "vfat") {
                efi = pm;
                break;
            }
        }
        emit confirmed(disk, efi, m_archSizeGb, m_mode);
    }

    void updateSizeSlider() {
        bool show = (m_mode == "dualboot" || m_mode == "freespace");
        m_sizeFrame->setVisible(show);
    }

private:
    QList<QVariantMap>    m_disks;
    QList<QVariantList>   m_partitions;
    int                   m_selectedDisk = -1;
    double                m_archSizeGb   = 40.0;
    QString               m_mode         = "wipe";

    QListWidget  *m_diskList;
    QLabel       *m_barLbl, *m_sizeLbl;
    QSlider      *m_sizeSlider;
    QFrame       *m_sizeFrame;
    QPushButton  *m_backBtn, *m_confirmBtn;

    void loadDisks() {
        QProcess p;
        p.start("lsblk", {"-J","-o","NAME,SIZE,MODEL,TYPE,FSTYPE,MOUNTPOINT,PARTTYPE,PKNAME,RM"});
        p.waitForFinished(5000);
        QJsonDocument doc = QJsonDocument::fromJson(p.readAllStandardOutput());
        QJsonArray devs = doc.object()["blockdevices"].toArray();

        m_disks.clear(); m_partitions.clear();
        for (const auto& devVal : devs) {
            QJsonObject dev = devVal.toObject();
            if (dev["type"].toString() != "disk") continue;
            if (dev["rm"].toBool()) continue; // skip removable (the ISO USB itself)

            QVariantMap dm;
            dm["name"]  = dev["name"].toString();
            dm["size"]  = dev["size"].toString();
            dm["model"] = dev["model"].toString();
            m_disks.append(dm);

            QVariantList parts;
            for (const auto& childVal : dev["children"].toArray()) {
                QJsonObject ch = childVal.toObject();
                QVariantMap pm;
                pm["name"]      = ch["name"].toString();
                pm["size"]      = ch["size"].toString();
                pm["fstype"]    = ch["fstype"].toString();
                pm["mountpoint"]= ch["mountpoint"].toString();
                pm["parttype"]  = ch["parttype"].toString();
                parts.append(pm);
            }
            m_partitions.append(parts);

            QString label = QString("/dev/%1  %2  %3")
                .arg(dm["name"].toString())
                .arg(dm["size"].toString())
                .arg(dm["model"].toString());
            m_diskList->addItem(label);
        }
    }

    void updateBar() {
        if (m_selectedDisk < 0 || m_selectedDisk >= m_partitions.size()) return;
        const auto& parts = m_partitions[m_selectedDisk];

        // Build a colored bar showing partition layout
        QString html = "<div style='display:flex;'>";
        QStringList colors = {"#e8557a","#ff6b9d","#9b59d0","#5a5068","#3d2a4a","#2e2b3d"};
        int ci = 0;
        for (const auto& pv : parts) {
            QVariantMap pm = pv.toMap();
            QString name   = pm["name"].toString();
            QString fstype = pm["fstype"].toString().isEmpty() ? "?" : pm["fstype"].toString();
            QString size   = pm["size"].toString();
            QString color  = colors[ci % colors.size()]; ci++;
            html += QString("<span style='background:%1;border-radius:4px;padding:4px 8px;margin:0 1px;font-size:10px;color:#12111a;'>%2 %3</span>")
                        .arg(color, name, size);
        }
        if (parts.isEmpty())
            html += QString("<span style='color:%1;font-size:11px;'>No partitions detected</span>").arg(Theme::TEXT3);
        html += "</div>";
        m_barLbl->setText(html);
    }
};

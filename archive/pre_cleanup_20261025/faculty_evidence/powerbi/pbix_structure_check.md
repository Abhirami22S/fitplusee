# PBIX structure check
File: `D:\bigdata\fitpulsee\FitPulse\powerbi\FitPulse_PowerBI_Dashboard.pbix`

| Check | Result | Detail |
|---|---|---|
| PBIX package opens as a zip | PASS | 87 entries, 4,403 KB |
| contains a data model | PASS | ['DataModel'] |
| contains a report definition (Layout or PBIR) | PASS | PBIR |
| page count | PASS | ['Fitness Overview', 'Activity and Sleep', 'Calorie Prediction', 'User Segmentation', 'Model Evaluation'] |
| page exists: Fitness Overview | PASS |  |
| page exists: Activity and Sleep | PASS |  |
| page exists: Calorie Prediction | PASS |  |
| page exists: User Segmentation | PASS |  |
| page exists: Model Evaluation | PASS |  |
| visuals found | PASS | 70 visuals |
| slicers present | PASS | 15 slicers |
| no visual references a nonexistent column or unknown measure | PASS | all field references resolve |

## Pages
* **Fitness Overview** - 17 visuals: card, clusteredColumnChart, lineClusteredColumnComboChart, scatterChart, slicer, tableEx, textbox
* **Activity and Sleep** - 18 visuals: card, clusteredColumnChart, lineChart, scatterChart, slicer, textbox
* **Calorie Prediction** - 14 visuals: card, clusteredColumnChart, lineChart, scatterChart, slicer, tableEx, textbox
* **User Segmentation** - 13 visuals: card, clusteredColumnChart, donutChart, scatterChart, slicer, tableEx, textbox
* **Model Evaluation** - 8 visuals: lineChart, slicer, tableEx, textbox

This check reads the file's metadata only. It does not render pages or test slicers; those are manual checks in Power BI Desktop (see BUILD_GUIDE.md section 8).
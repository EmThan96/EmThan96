<?xml version="1.0" encoding="utf-8"?>
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
    <Script>
        <Name>gbc_engineers\hbt_fixture\HBTFixture.py</Name>
        <Title>HBT Fixture</Title>
        <Version>2.0</Version>
        <ReadLastInput>True</ReadLastInput>
    </Script>
    <!-- Company library folder: put the shared network path as default value of the parameter
         "LibraryPath" below, e.g. \\server\Allplan\HBT_Library . Empty = Allplan Usr\HBT_Library -->
    <Constants>
      <Constant>
        <Name>REF_POINT</Name>
        <Value>1</Value>
        <ValueType>Integer</ValueType>
      </Constant>
      <Constant>
        <Name>DIR_POINT</Name>
        <Value>2</Value>
        <ValueType>Integer</ValueType>
      </Constant>
      <Constant>
        <Name>MODE_SINGLE</Name>
        <Value>1</Value>
        <ValueType>Integer</ValueType>
      </Constant>
      <Constant>
        <Name>MODE_POLYLINE</Name>
        <Value>2</Value>
        <ValueType>Integer</ValueType>
      </Constant>
      <Constant>
        <Name>LOAD_SAVED</Name>
        <Value>1001</Value>
        <ValueType>Integer</ValueType>
      </Constant>
      <Constant>
        <Name>REFRESH_LIBRARY</Name>
        <Value>1002</Value>
        <ValueType>Integer</ValueType>
      </Constant>
    </Constants>
    <Page>
      <Name>HBTPage</Name>
      <Text>HBT</Text>
      <Parameters>
        <Parameter>
          <Name>ProductExp</Name>
          <Text>Product</Text>
          <ValueType>Expander</ValueType>
          <Parameters>
            <Parameter>
              <Name>Rows</Name>
              <Text>Rebar rows</Text>
              <Value>1</Value>
              <ValueType>RadioButtonGroup</ValueType>
              <Parameters>
                <Parameter>
                  <Name>RowsSingle</Name>
                  <Text>Single-row</Text>
                  <Value>1</Value>
                  <ValueType>RadioButton</ValueType>
                </Parameter>
                <Parameter>
                  <Name>RowsDouble</Name>
                  <Text>Double-row</Text>
                  <Value>2</Value>
                  <ValueType>RadioButton</ValueType>
                </Parameter>
              </Parameters>
            </Parameter>
            <Parameter>
              <Name>Casing</Name>
              <Text>Casing type</Text>
              <Value>HBT 85</Value>
              <ValueList>CasingList</ValueList>
              <ValueType>StringComboBox</ValueType>
            </Parameter>
            <Parameter>
              <Name>RebarType</Name>
              <Text>Rebar type</Text>
              <Value>Type 1 - hook y (standard)</Value>
              <ValueList>RebarTypeList</ValueList>
              <ValueType>StringComboBox</ValueType>
            </Parameter>
            <Parameter>
              <Name>Diameter</Name>
              <Text>Rebar diameter [mm]</Text>
              <Value>10</Value>
              <ValueList>DiameterList</ValueList>
              <ValueType>StringComboBox</ValueType>
            </Parameter>
            <Parameter>
              <Name>Spacing</Name>
              <Text>Rebar spacing s [cm]</Text>
              <Value>15</Value>
              <ValueList>SpacingList</ValueList>
              <ValueType>StringComboBox</ValueType>
            </Parameter>
            <Parameter>
              <Name>ElementLength</Name>
              <Text>Element length L [mm]</Text>
              <Value>1250</Value>
              <ValueList>LengthList</ValueList>
              <ValueType>StringComboBox</ValueType>
              <Visible>PlacementMode == 1</Visible>
            </Parameter>
            <Parameter>
              <Name>CustomLength</Name>
              <Text>Custom length L</Text>
              <Value>1000</Value>
              <ValueType>Length</ValueType>
              <Visible>PlacementMode == 1 and ElementLength == "Custom"</Visible>
            </Parameter>
            <Parameter>
              <Name>HBTStrip</Name>
              <Text>HBT Strip (HBT-S)</Text>
              <Value>False</Value>
              <ValueType>CheckBox</ValueType>
              <Visible>Rows == 2</Visible>
            </Parameter>
          </Parameters>
        </Parameter>
        <Parameter>
          <Name>DimExp</Name>
          <Text>Rebar dimensions</Text>
          <ValueType>Expander</ValueType>
          <Parameters>
            <Parameter>
              <Name>StandardDims</Name>
              <Text>Standard dimensions (catalogue)</Text>
              <Value>True</Value>
              <ValueType>CheckBox</ValueType>
            </Parameter>
            <Parameter>
              <Name>AnchorLength</Name>
              <Text>h (component 1)</Text>
              <Value>170</Value>
              <ValueType>Length</ValueType>
              <Enable>StandardDims == False</Enable>
            </Parameter>
            <Parameter>
              <Name>ConnectionLength</Name>
              <Text>lü (connected component)</Text>
              <Value>390</Value>
              <ValueType>Length</ValueType>
              <Enable>StandardDims == False</Enable>
            </Parameter>
            <Parameter>
              <Name>LegName</Name>
              <Text>Leg</Text>
              <Value></Value>
              <ValueType>String</ValueType>
              <Enable>False</Enable>
              <Visible>LegName != ""</Visible>
            </Parameter>
            <Parameter>
              <Name>LegLength</Name>
              <Text>Leg length (y / b / b1 / b2)</Text>
              <Value>95</Value>
              <ValueType>Length</ValueType>
              <Enable>StandardDims == False</Enable>
              <Visible>LegName != ""</Visible>
            </Parameter>
            <Parameter>
              <Name>HMin</Name>
              <Text>hmin</Text>
              <Value>120</Value>
              <ValueType>Length</ValueType>
              <Enable>False</Enable>
            </Parameter>
            <Parameter>
              <Name>LuMax</Name>
              <Text>lü,max</Text>
              <Value>0</Value>
              <ValueType>Length</ValueType>
              <Enable>False</Enable>
            </Parameter>
            <Parameter>
              <Name>LMin</Name>
              <Text>Lmin (custom length)</Text>
              <Value>800</Value>
              <ValueType>Length</ValueType>
              <Enable>False</Enable>
            </Parameter>
          </Parameters>
        </Parameter>
        <Parameter>
          <Name>BendExp</Name>
          <Text>Bends (mandrel D)</Text>
          <ValueType>Expander</ValueType>
          <Parameters>
            <Parameter>
              <Name>MandrelCatalogue</Name>
              <Text>D/Ø where catalogue states D = 10Ø</Text>
              <Value>10</Value>
              <ValueType>Double</ValueType>
            </Parameter>
            <Parameter>
              <Name>MandrelEC2</Name>
              <Text>D/Ø other bends (EC2 default 4)</Text>
              <Value>4</Value>
              <ValueType>Double</ValueType>
            </Parameter>
          </Parameters>
        </Parameter>
        <Parameter>
          <Name>DataExp</Name>
          <Text>Catalogue data</Text>
          <ValueType>Expander</ValueType>
          <Parameters>
            <Parameter>
              <Name>CasingWidth</Name>
              <Text>Casing width B</Text>
              <Value>0</Value>
              <ValueType>Length</ValueType>
              <Enable>False</Enable>
            </Parameter>
            <Parameter>
              <Name>CasingDepth</Name>
              <Text>Casing height H2</Text>
              <Value>0</Value>
              <ValueType>Length</ValueType>
              <Enable>False</Enable>
            </Parameter>
            <Parameter>
              <Name>RebarWidth</Name>
              <Text>Rebar width b</Text>
              <Value>0</Value>
              <ValueType>Length</ValueType>
              <Enable>False</Enable>
              <Visible>Rows == 2</Visible>
            </Parameter>
            <Parameter>
              <Name>BarCount</Name>
              <Text>Number of rebars</Text>
              <Value>0</Value>
              <ValueType>Integer</ValueType>
              <Enable>False</Enable>
            </Parameter>
            <Parameter>
              <Name>EndSpacing</Name>
              <Text>End spacing a</Text>
              <Value>0</Value>
              <ValueType>Length</ValueType>
              <Enable>False</Enable>
            </Parameter>
            <Parameter>
              <Name>InfoText</Name>
              <Text>Check</Text>
              <Value></Value>
              <ValueType>String</ValueType>
              <Enable>False</Enable>
            </Parameter>
            <Parameter>
              <Name>CatalogueFile</Name>
              <Text>Catalogue file (empty = default)</Text>
              <Value></Value>
              <ValueType>String</ValueType>
            </Parameter>
          </Parameters>
        </Parameter>
      </Parameters>
    </Page>
    <Page>
      <Name>PlacementPage</Name>
      <Text>Placement</Text>
      <Parameters>
        <Parameter>
          <Name>PlacementExp</Name>
          <Text>Placement</Text>
          <ValueType>Expander</ValueType>
          <Parameters>
            <Parameter>
              <Name>PlacementMode</Name>
              <Text>Placement</Text>
              <Value>1</Value>
              <ValueType>RadioButtonGroup</ValueType>
              <Parameters>
                <Parameter>
                  <Name>ModeSingle</Name>
                  <Text>Single element (2 points)</Text>
                  <Value>1</Value>
                  <ValueType>RadioButton</ValueType>
                </Parameter>
                <Parameter>
                  <Name>ModePolyline</Name>
                  <Text>Polyline (auto 1250 / 800 / custom)</Text>
                  <Value>2</Value>
                  <ValueType>RadioButton</ValueType>
                </Parameter>
              </Parameters>
            </Parameter>
            <Parameter>
              <Name>FacePlane</Name>
              <Text>Formwork face</Text>
              <Value>2</Value>
              <ValueType>RadioButtonGroup</ValueType>
              <Parameters>
                <Parameter>
                  <Name>FaceHorizontal</Name>
                  <Text>Horizontal face</Text>
                  <Value>1</Value>
                  <ValueType>RadioButton</ValueType>
                </Parameter>
                <Parameter>
                  <Name>FaceVerticalBoxHoriz</Name>
                  <Text>Vertical face, box horizontal</Text>
                  <Value>2</Value>
                  <ValueType>RadioButton</ValueType>
                </Parameter>
                <Parameter>
                  <Name>FaceVerticalBoxVert</Name>
                  <Text>Vertical face, box vertical</Text>
                  <Value>3</Value>
                  <ValueType>RadioButton</ValueType>
                </Parameter>
              </Parameters>
            </Parameter>
            <Parameter>
              <Name>VerticalFaceAngle</Name>
              <Text>Face normal for vertical segments</Text>
              <Value>0</Value>
              <ValueType>Angle</ValueType>
              <Visible>PlacementMode == 2</Visible>
            </Parameter>
            <Parameter>
              <Name>FlipSide</Name>
              <Text>Flip component 1 side</Text>
              <Value>False</Value>
              <ValueType>CheckBox</ValueType>
            </Parameter>
            <Parameter>
              <Name>BarState</Name>
              <Text>Bar state</Text>
              <Value>1</Value>
              <ValueType>RadioButtonGroup</ValueType>
              <Parameters>
                <Parameter>
                  <Name>BarsStraightened</Name>
                  <Text>Straightened (installed)</Text>
                  <Value>1</Value>
                  <ValueType>RadioButton</ValueType>
                </Parameter>
                <Parameter>
                  <Name>BarsDelivered</Name>
                  <Text>Bent in casing (delivered)</Text>
                  <Value>2</Value>
                  <ValueType>RadioButton</ValueType>
                </Parameter>
              </Parameters>
            </Parameter>
            <Parameter>
              <Name>CutBoxVolume</Name>
              <Text>Cut casing volume from precast element</Text>
              <Value>False</Value>
              <ValueType>CheckBox</ValueType>
            </Parameter>
          </Parameters>
        </Parameter>
        <Parameter>
          <Name>AttrExp</Name>
          <Text>Attributes</Text>
          <ValueType>Expander</ValueType>
          <Parameters>
            <Parameter>
              <Name>PlanText</Name>
              <Text>Plan_text (automatic)</Text>
              <Value></Value>
              <ValueType>String</ValueType>
              <Enable>False</Enable>
            </Parameter>
            <Parameter>
              <Name>Answer1</Name>
              <Text>Answer 1</Text>
              <Value></Value>
              <ValueType>String</ValueType>
            </Parameter>
            <Parameter>
              <Name>Answer2</Name>
              <Text>Answer 2</Text>
              <Value></Value>
              <ValueType>String</ValueType>
            </Parameter>
            <Parameter>
              <Name>Answer3</Name>
              <Text>Answer 3</Text>
              <Value></Value>
              <ValueType>String</ValueType>
            </Parameter>
            <Parameter>
              <Name>Answer4</Name>
              <Text>Answer 4</Text>
              <Value></Value>
              <ValueType>String</ValueType>
            </Parameter>
            <Parameter>
              <Name>Answer5</Name>
              <Text>Answer 5</Text>
              <Value></Value>
              <ValueType>String</ValueType>
            </Parameter>
          </Parameters>
        </Parameter>
        <Parameter>
          <Name>LibraryExp</Name>
          <Text>Company library</Text>
          <ValueType>Expander</ValueType>
          <Parameters>
            <Parameter>
              <Name>LibraryPath</Name>
              <Text>Company library folder (set default here)</Text>
              <Value></Value>
              <ValueType>String</ValueType>
            </Parameter>
            <Parameter>
              <Name>LibraryFolder</Name>
              <Text>Folder in use</Text>
              <Value></Value>
              <ValueType>String</ValueType>
              <Enable>False</Enable>
            </Parameter>
            <Parameter>
              <Name>LibraryStatus</Name>
              <Text>Status</Text>
              <Value></Value>
              <ValueType>String</ValueType>
              <Enable>False</Enable>
            </Parameter>
            <Parameter>
              <Name>SavedItem</Name>
              <Text>Saved products</Text>
              <Value></Value>
              <ValueList>SavedList</ValueList>
              <ValueType>StringComboBox</ValueType>
            </Parameter>
            <Parameter>
              <Name>LibraryButtons</Name>
              <Text></Text>
              <ValueType>Row</ValueType>
              <Parameters>
                <Parameter>
                  <Name>LoadSavedButton</Name>
                  <Text>Load selected</Text>
                  <EventId>LOAD_SAVED</EventId>
                  <ValueType>Button</ValueType>
                </Parameter>
                <Parameter>
                  <Name>RefreshButton</Name>
                  <Text>Refresh list</Text>
                  <EventId>REFRESH_LIBRARY</EventId>
                  <ValueType>Button</ValueType>
                </Parameter>
              </Parameters>
            </Parameter>
          </Parameters>
        </Parameter>
        <Parameter>
          <Name>FormatExp</Name>
          <Text>Format</Text>
          <ValueType>Expander</ValueType>
          <Parameters>
            <Parameter>
              <Name>CommonProp</Name>
              <Text></Text>
              <Value></Value>
              <ValueType>CommonProperties</ValueType>
            </Parameter>
            <Parameter>
              <Name>BarColor</Name>
              <Text>Bar color</Text>
              <Value>6</Value>
              <ValueType>Color</ValueType>
            </Parameter>
          </Parameters>
        </Parameter>
      </Parameters>
    </Page>
    <Page>
      <Name>__HiddenPage__</Name>
      <Text></Text>
      <Parameters>
        <Parameter>
          <Name>InputMode</Name>
          <Text></Text>
          <Value>1</Value>
          <ValueType>Integer</ValueType>
        </Parameter>
        <Parameter>
          <Name>CasingList</Name>
          <Text></Text>
          <Value>HBT 85</Value>
          <ValueType>String</ValueType>
        </Parameter>
        <Parameter>
          <Name>RebarTypeList</Name>
          <Text></Text>
          <Value>Type 1 - hook y (standard)</Value>
          <ValueType>String</ValueType>
        </Parameter>
        <Parameter>
          <Name>DiameterList</Name>
          <Text></Text>
          <Value>10</Value>
          <ValueType>String</ValueType>
        </Parameter>
        <Parameter>
          <Name>SpacingList</Name>
          <Text></Text>
          <Value>15</Value>
          <ValueType>String</ValueType>
        </Parameter>
        <Parameter>
          <Name>LengthList</Name>
          <Text></Text>
          <Value>1250|800|Custom</Value>
          <ValueType>String</ValueType>
        </Parameter>
        <Parameter>
          <Name>SavedList</Name>
          <Text></Text>
          <Value></Value>
          <ValueType>String</ValueType>
        </Parameter>
      </Parameters>
    </Page>
</Element>
